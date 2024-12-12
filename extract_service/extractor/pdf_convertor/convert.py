import warnings

from marker.pdf.images import render_image

warnings.filterwarnings("ignore", category=UserWarning) # Filter torch pytree user warnings

import os
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1" # For some reason, transformers decided to use .isin for a simple op, which is not supported on MPS


import pypdfium2 as pdfium # Needs to be at the top to avoid warnings
from PIL import Image

from marker.utils import flush_cuda_memory
from marker.debug.data import dump_bbox_debug_data, draw_page_debug_images
from marker.layout.layout import surya_layout, annotate_block_types
from marker.layout.order import surya_order, sort_blocks_in_reading_order
from marker.ocr.lang import replace_langs_with_codes, validate_langs
from marker.ocr.detection import surya_detection
from marker.ocr.recognition import run_ocr
from marker.pdf.extract_text import get_text_blocks
from marker.cleaners.headers import filter_header_footer, filter_common_titles
from marker.equations.equations import replace_equations
from marker.pdf.utils import find_filetype
from marker.cleaners.code import identify_code_blocks, indent_blocks
from marker.cleaners.bullets import replace_bullets
from marker.cleaners.headings import split_heading_blocks, infer_heading_levels
from marker.cleaners.fontstyle import find_bold_italic
from marker.postprocessors.markdown import merge_spans, merge_lines, get_full_text
from marker.cleaners.text import cleanup_text
from marker.images.extract import extract_images
from marker.images.save import images_to_dict
from marker.cleaners.toc import compute_toc

from typing import Generator, List, Dict, Tuple, Optional
from marker.settings import settings

from .tables import format_table_in_page

def custom_convert_pdf(
        fname: str,
        model_lst: List,
        max_pages: int = None,
        start_page: int = None,
        metadata: Optional[Dict] = None,
        langs: Optional[List[str]] = None,
        batch_multiplier: int = 1,
        ocr_all_pages: bool = False
) -> Generator[Tuple[str, Dict[str, Image.Image], Dict, Dict, int], None, None]:
    message = "success"

    ocr_all_pages = ocr_all_pages or settings.OCR_ALL_PAGES

    if metadata:
        langs = metadata.get("languages", langs)

    langs = replace_langs_with_codes(langs)
    validate_langs(langs)

    # Find the filetype
    filetype = find_filetype(fname)

    # Setup output metadata
    out_meta = {
        "languages": langs,
        "filetype": filetype,
    }

    if filetype == "other": # We can't process this file
        yield "", {}, out_meta
        return

    # Get initial text blocks from the pdf
    doc = pdfium.PdfDocument(fname)
    pages, toc = get_text_blocks(
        doc,
        fname,
        max_pages=max_pages,
        start_page=start_page
    )
    out_meta.update({
        "pdf_toc": toc,
        "pages": len(pages),
    })

    # Trim pages from doc to align with start page
    if start_page:
        for page_idx in range(start_page):
            doc.del_page(0)

    max_len = min(len(pages), len(doc))
    lowres_images = [render_image(doc[pnum], dpi=settings.SURYA_DETECTOR_DPI) for pnum in range(max_len)]

    # Unpack models from list
    texify_model, layout_model, order_model, detection_model, ocr_model, table_rec_model = model_lst

    for pnum, (page, lowres_image) in enumerate(zip(pages, lowres_images)):
        # Identify text lines, layout, reading order
        surya_detection([lowres_image], [page], detection_model, batch_multiplier=batch_multiplier)

        # OCR for the page
        [page], ocr_stats = run_ocr(doc, [page], langs, ocr_model, batch_multiplier=batch_multiplier, ocr_all_pages=ocr_all_pages)
        flush_cuda_memory()
        out_meta["ocr_stats"] = ocr_stats

        if len([b for b in page.blocks]) == 0:
            message = f"Could not extract any text blocks for page {pnum + 1} in {fname}"
            yield "", {}, out_meta, [], pnum, message
            continue

        surya_layout([lowres_image], [page], layout_model, batch_multiplier=batch_multiplier)

        # Find headers and footers
        bad_span_ids = filter_header_footer([page])
        out_meta["block_stats"] = {"header_footer": len(bad_span_ids)}

        # Add block types from layout
        annotate_block_types([page])

        # Sort from reading order
        surya_order([lowres_image], [page], order_model, batch_multiplier=batch_multiplier)
        sort_blocks_in_reading_order([page])

        # Dump debug data if flags are set
        draw_page_debug_images(fname, [page])
        dump_bbox_debug_data(fname, [page])

        # Fix code blocks
        code_block_count = identify_code_blocks([page])
        out_meta["block_stats"]["code"] = code_block_count
        indent_blocks([page])

        # Fix table blocks
        table_count, table_data = format_table_in_page(page, doc, fname, detection_model, table_rec_model, ocr_model)
        out_meta["block_stats"]["table"] = table_count

        for block in page.blocks:
            block.filter_spans(bad_span_ids)
            block.filter_bad_span_types()

        filtered, eq_stats = replace_equations(
            doc,
            [page],
            texify_model,
            batch_multiplier=batch_multiplier
        )
        flush_cuda_memory()
        out_meta["block_stats"]["equations"] = eq_stats

        # Extract images and figures if enabled
        if settings.EXTRACT_IMAGES:
            extract_images([doc[pnum]], [page])

        # Split out headers
        split_heading_blocks([page])
        infer_heading_levels([page])
        find_bold_italic([page])

        # Use headers to compute a table of contents
        out_meta["computed_toc"] = compute_toc([page])

        # Copy to avoid changing original data
        merged_lines = merge_spans(filtered)
        text_blocks = merge_lines(merged_lines)
        text_blocks = filter_common_titles(text_blocks)
        full_text = get_full_text(text_blocks)

        # Handle empty blocks being joined
        full_text = cleanup_text(full_text)

        # Replace bullet characters with a -
        full_text = replace_bullets(full_text)

        doc_images = images_to_dict([page])

        yield full_text, doc_images, out_meta, table_data, pnum, message