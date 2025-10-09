# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import importlib.util
import logging
import re
import xml.dom.minidom
import zipfile

from odoo import api, models
from odoo.tools.lru import LRU

_logger = logging.getLogger(__name__)

if not importlib.util.find_spec('pdfminer.high_level'):
    _logger.warning("Attachment indexation of PDF documents is unavailable because the 'pdfminer.six' Python library cannot be found on the system. "
                    "You may install it from https://pypi.org/project/pdfminer.six/ (e.g. `pip3 install pdfminer.six`)")

FTYPES = ['docx', 'pptx', 'xlsx', 'opendoc', 'pdf']


index_content_cache = LRU(1)

def textToString(element):
    buff = u""
    for node in element.childNodes:
        if node.nodeType == xml.dom.Node.TEXT_NODE:
            buff += node.nodeValue
        elif node.nodeType == xml.dom.Node.ELEMENT_NODE:
            buff += textToString(node)
    return buff


def _clean_pdf_content(buf):
    """
    Clean the PDF content by removing unwanted characters and formatting.
    Remove NUL characters and Normalizes line breaks and whitespace for cleaner
    indexing.
    """
    buf = buf.replace('\x00', '')
    buf = buf.replace('\r\n', '\n').replace('\r', '\n')
    paragraphs = re.split(r'\n\s*\n', buf)
    paragraphs = [re.sub(r'[ \t]+', ' ', p.strip()) for p in paragraphs]
    return '\n'.join(paragraphs)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _index_docx(self, bin_data):
        '''Index Microsoft .docx documents'''
        buf = u""
        f = io.BytesIO(bin_data)
        if zipfile.is_zipfile(f):
            try:
                zf = zipfile.ZipFile(f)
                content = xml.dom.minidom.parseString(zf.read("word/document.xml"))
                for val in ["w:p", "w:h", "text:list"]:
                    for element in content.getElementsByTagName(val):
                        buf += textToString(element) + "\n"
            except Exception:
                pass
        return buf

    def _index_pptx(self, bin_data):
        '''Index Microsoft .pptx documents'''

        buf = u""
        f = io.BytesIO(bin_data)
        if zipfile.is_zipfile(f):
            try:
                zf = zipfile.ZipFile(f)
                zf_filelist = [x for x in zf.namelist() if x.startswith('ppt/slides/slide')]
                for i in range(1, len(zf_filelist) + 1):
                    content = xml.dom.minidom.parseString(zf.read('ppt/slides/slide%s.xml' % i))
                    for val in ["a:t"]:
                        for element in content.getElementsByTagName(val):
                            buf += textToString(element) + "\n"
            except Exception:
                pass
        return buf

    def _index_xlsx(self, bin_data):
        '''Index Microsoft .xlsx documents'''

        buf = u""
        f = io.BytesIO(bin_data)
        if zipfile.is_zipfile(f):
            try:
                zf = zipfile.ZipFile(f)
                # Load shared strings if present
                shared_strings = []
                if "xl/sharedStrings.xml" in zf.namelist():
                    ss_content = xml.dom.minidom.parseString(zf.read("xl/sharedStrings.xml"))
                    for si in ss_content.getElementsByTagName("si"):
                        text = ""
                        for t in si.getElementsByTagName("t"):
                            text += textToString(t)
                        shared_strings.append(text)

                sheet_files = [n for n in zf.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
                for sheet_file in sorted(sheet_files):
                    sheet_lines = []
                    sheet_content = xml.dom.minidom.parseString(zf.read(sheet_file))
                    rows = sheet_content.getElementsByTagName("row")
                    for row in rows:
                        cells = row.getElementsByTagName("c")
                        row_values = []
                        for cell in cells:
                            cell_type = cell.getAttribute("t")
                            # inlineStr support for shared strings
                            if cell_type == "inlineStr":
                                is_elements = cell.getElementsByTagName("is")
                                if is_elements:
                                    t_nodes = is_elements[0].getElementsByTagName("t")
                                    if t_nodes:
                                        row_values.append(textToString(t_nodes[0]))
                                        continue
                            v_elements = cell.getElementsByTagName("v")
                            if not v_elements:
                                continue
                            value = textToString(v_elements[0])
                            if cell_type == "s":
                                idx = int(value)
                                value = shared_strings[idx]
                            row_values.append(value)
                        if row_values:
                            sheet_lines.append(", ".join(row_values))
                    if sheet_lines:
                        buf += "\n".join(sheet_lines) + "\n\n"
            except Exception:
                pass
        return buf

    def _index_opendoc(self, bin_data):
        '''Index OpenDocument documents (.odt, .ods...)'''

        buf = u""
        f = io.BytesIO(bin_data)
        if zipfile.is_zipfile(f):
            try:
                zf = zipfile.ZipFile(f)
                content = xml.dom.minidom.parseString(zf.read("content.xml"))
                mime_type = zf.read("mimetype").decode("utf-8").strip()
                if mime_type == "application/vnd.oasis.opendocument.spreadsheet":
                    tables = content.getElementsByTagName("table:table")
                    if tables:
                        # Extract rows and cells as CSV
                        for table in tables:
                            table_lines = []
                            rows = table.getElementsByTagName("table:table-row")
                            for row in rows:
                                cells = row.getElementsByTagName("table:table-cell")
                                row_values = []
                                for cell in cells:
                                    # Concatenate all paragraphs within the cell
                                    cell_paragraphs = cell.getElementsByTagName("text:p")
                                    cell_text_parts = []
                                    for p in cell_paragraphs:
                                        text_part = textToString(p)
                                        if text_part.strip():
                                            cell_text_parts.append(text_part)
                                    if cell_text_parts:
                                        row_values.append(" ".join(cell_text_parts))
                                if row_values:
                                    table_lines.append(", ".join(row_values))
                            if table_lines:
                                buf += "\n".join(table_lines) + "\n\n"
                else:
                    for val in ["text:p", "text:h", "text:list"]:
                        for element in content.getElementsByTagName(val):
                            buf += textToString(element) + "\n"
            except Exception:
                pass
        return buf

    def _index_pdf(self, bin_data):
        '''Index PDF documents'''
        if not bin_data.startswith(b'%PDF-'):
            return ""
        try:
            from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter  # noqa: PLC0415
            from pdfminer.converter import TextConverter  # noqa: PLC0415
            from pdfminer.layout import LAParams  # noqa: PLC0415
            from pdfminer.pdfpage import PDFPage  # noqa: PLC0415
            logging.getLogger("pdfminer").setLevel(logging.CRITICAL)
        except ImportError:
            # warned already during init of module
            return ""
        f = io.BytesIO(bin_data)
        try:
            resource_manager = PDFResourceManager()
            laparams = LAParams(
                line_margin=0.5,
                char_margin=2.0,
                word_margin=0.1,
                boxes_flow=0.5,
                detect_vertical=True,
            )

            with io.StringIO() as content, TextConverter(
                resource_manager,
                content,
                laparams=laparams
            ) as device:
                interpreter = PDFPageInterpreter(resource_manager, device)
                for page in PDFPage.get_pages(f):
                    interpreter.process_page(page)

                buf = content.getvalue()

            return _clean_pdf_content(buf)
        except Exception:  # noqa: BLE001
            return ""

    @api.model
    def _index(self, bin_data, mimetype, checksum=None):
        if checksum:
            cached_content = index_content_cache.get(checksum)
            if cached_content:
                return cached_content
        res = False
        for ftype in FTYPES:
            buf = getattr(self, '_index_%s' % ftype)(bin_data)
            if buf:
                res = buf.replace('\x00', '')
                break

        res = res or super(IrAttachment, self)._index(bin_data, mimetype, checksum=checksum)
        if checksum:
            index_content_cache[checksum] = res
        return res

    def copy(self, default=None):
        for attachment in self:
            index_content_cache[attachment.checksum] = attachment.index_content
        return super().copy(default=default)
