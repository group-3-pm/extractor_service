from tqdm import tqdm
from pypdfium2 import PdfDocument
from tabled.assignment import assign_rows_columns
from tabled.formats import formatter
from tabled.inference.detection import merge_tables

from surya.input.pdflines import get_page_text_lines
from tabled.inference.recognition import get_cells, recognize_tables

from marker.pdf.images import render_image
from marker.schema.bbox import rescale_bbox
from marker.schema.block import Line, Span, Block
from marker.schema.page import Page
from typing import List
from marker.ocr.recognition import get_batch_size as get_ocr_batch_size
from marker.ocr.detection import get_batch_size as get_detector_batch_size

from marker.settings import settings
from marker.tables.table import get_table_boxes, get_batch_size

def format_table_in_page(page: Page, doc: PdfDocument, fname: str, detection_model, table_rec_model, ocr_model):
    """
    Processes and formats tables within a single page of a PDF document.

    Parameters:
    - page (Page): The page object to process.
    - doc (PdfDocument): The PDF document object.
    - fname (str): The filename of the PDF document.
    - detection_model: The table detection model.
    - table_rec_model: The table recognition model.
    - ocr_model: The OCR model for text recognition.

    Returns:
    - int: The number of tables detected and formatted on the page.
    - list: Formatted data of tables on the page including markdown and CSV representations.
    """
    # Disable tqdm output for cell detection
    tqdm.disable = True

    # Process table boxes, images, and necessary information for this page only
    table_imgs, table_boxes, table_counts, table_text_lines, img_sizes = get_table_boxes([page], doc, fname)

    # Detect cells and identify regions needing OCR
    cells, needs_ocr = get_cells(table_imgs, table_boxes, img_sizes, table_text_lines,
                                 [detection_model, detection_model.processor],
                                 detect_boxes=settings.OCR_ALL_PAGES,
                                 detector_batch_size=get_detector_batch_size())
    tqdm.disable = False

    # Recognize and assign cells within tables
    table_rec = recognize_tables(table_imgs, cells, needs_ocr,
                                 [table_rec_model, table_rec_model.processor, ocr_model, ocr_model.processor],
                                 table_rec_batch_size=get_batch_size(),
                                 ocr_batch_size=get_ocr_batch_size())

    # Format tables as Markdown and CSV
    cells = [assign_rows_columns(tr, im_size) for tr, im_size in zip(table_rec, img_sizes)]
    table_md = [formatter("markdown", cell)[0] for cell in cells]
    table_csv = [formatter("csv", cell)[0] for cell in cells]

    # Initialize table data for the current page
    table_count = 0
    page_table_data = []  # Data for tables on this specific page

    # If no tables detected, return early
    page_table_count = table_counts[0]
    if page_table_count == 0:
        return 0, []

    # Determine insertion points for each table block
    table_insert_points = {}
    blocks_to_remove = set()
    pnum = page.pnum
    highres_size = img_sizes[0]
    page_table_boxes = table_boxes[:page_table_count]

    # Identify blocks overlapping with table boxes
    for table_idx, table_box in enumerate(page_table_boxes):
        lowres_table_box = rescale_bbox([0, 0, highres_size[0], highres_size[1]], page.bbox, table_box)

        for block_idx, block in enumerate(page.blocks):
            intersect_pct = block.intersection_pct(lowres_table_box)
            if intersect_pct > settings.TABLE_INTERSECTION_THRESH and block.block_type == "Table":
                if table_idx not in table_insert_points:
                    table_insert_points[table_idx] = max(0, block_idx - len(blocks_to_remove))
                blocks_to_remove.add(block_idx)

    # Prepare new page blocks excluding overlapping ones
    new_page_blocks = [block for block_idx, block in enumerate(page.blocks) if block_idx not in blocks_to_remove]

    # Insert formatted tables into new page blocks at designated points
    for table_idx, table_box in enumerate(page_table_boxes):
        if table_idx not in table_insert_points:
            table_count += 1
            continue

        markdown = table_md[table_count]
        csv_data = table_csv[table_count]

        # Record table data for the page
        page_table_data.append({
            "table_index": table_idx,
            "content": csv_data,
            "bbox": table_box
        })

        # Create a new table block
        table_block = Block(
            bbox=table_box,
            block_type="Table",
            pnum=pnum,
            lines=[Line(
                bbox=table_box,
                spans=[Span(
                    bbox=table_box,
                    span_id=f"{table_idx}_table",
                    font="Table",
                    font_size=0,
                    font_weight=0,
                    block_type="Table",
                    text=markdown
                )]
            )]
        )

        # Insert the table block at the calculated position
        insert_point = table_insert_points[table_idx]
        insert_point = min(insert_point, len(new_page_blocks))
        new_page_blocks.insert(insert_point, table_block)
        table_count += 1
    table_data = {
        "page_number": pnum,
        "tables": page_table_data
    }

    # Update page blocks with new content
    page.blocks = new_page_blocks
    return table_count, table_data
