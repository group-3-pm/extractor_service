import os
import json
from docx2md.docxfile import DocxFile
from .doc_convertor.convert import Converter
from docx2md.docxmedia import DocxMedia

class DocxToMarkdown:
    def __init__(self, use_md_table=True, debug=False):
        self.use_md_table = use_md_table
        self.debug = debug

    def convert(self, src, dst):
        """Convert a DOCX file to Markdown."""
        self._check_target_dir(dst)
        target_dir = os.path.dirname(dst)
        
        # Load DOCX
        docx = self._create_docx(src)
        
        # Save debug files if enabled
        if self.debug:
            self._save_keyfile(docx, target_dir)
        
        # Convert to Markdown
        media = DocxMedia(docx)
        md_text = self._convert(docx, target_dir, media)
        # self._save_md(dst, md_text)
        
        self._save_json(dst, md_text)
        # Save media files
        media.save(target_dir)

    def _create_docx(self, file):
        try:
            return DocxFile(file)
        except Exception as e:
            raise RuntimeError(f"Error loading DOCX file: {e}")
    
    def _check_target_dir(self, file):
        dir = os.path.dirname(file)
        if dir and not os.path.exists(dir):
            os.makedirs(dir)

    def _save_keyfile(self, docx, target_dir):
        def save_xml(file, text):
            with open(file, "wb") as f:
                f.write(text)

        save_xml(os.path.join(target_dir, "document.xml"), docx.document())
        save_xml(os.path.join(target_dir, "document.xml.rels"), docx.rels())

    def _convert(self, docx, target_dir, media):
        xml_text = docx.document()
        converter = Converter(xml_text, media, self.use_md_table)
        return converter.convert()

    def _save_md(self, file, text):
        if isinstance(text, list):
            # Trích xuất văn bản từ các trang (giả sử mỗi phần tử là một dict với key 'text')
            text = "\n\n---PAGE BREAK Test---\n\n".join([page['images'] for page in text])  # Kết hợp văn bản của các trang
        with open(file, "w", encoding="utf-8") as f:
            f.write(text)

    def _save_json(self, file, data):
            """Save data as a JSON file."""
            with open(file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)  # `indent=4` to format the JSON
if __name__ == "__main__":
    converter = DocxToMarkdown()
    converter.convert("test.docx", "test.json")
