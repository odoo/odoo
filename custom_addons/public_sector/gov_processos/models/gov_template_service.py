import base64
import csv
import html
import io
import json
import re
import zipfile
from xml.etree import ElementTree as ET

from odoo.exceptions import UserError


class GovTemplateService:
    _HTML_TAG_RE = re.compile(r"<[^>]+>")
    _PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")
    _LATEX_COMMAND_RE = re.compile(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?")
    _TYPST_COMMAND_RE = re.compile(r"#[a-zA-Z_][a-zA-Z0-9_]*(?:\[[^\]]*\])?(?:\([^)]*\))?")
    _MARKDOWN_PREFIX_RE = re.compile(r"^\s{0,3}(#{1,6}|\*|-|\+|\d+\.)\s*")
    _XLSX_NS = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    _SOURCE_FORMAT_SELECTION = [
        ("latex", "LaTeX"),
        ("typst", "Typst"),
        ("markdown", "Markdown"),
        ("html", "HTML"),
        ("csv", "CSV"),
        ("xlsx", "XLSX"),
        ("xls", "XLS"),
        ("pdf", "PDF"),
        ("text", "Texto"),
        ("unknown", "Outro"),
    ]
    _TARGET_FORMAT_SELECTION = [
        ("latex", "LaTeX → PDF"),
        ("typst", "Typst → PDF"),
        ("html", "HTML"),
    ]

    @classmethod
    def get_source_format_selection(cls):
        return list(cls._SOURCE_FORMAT_SELECTION)

    @classmethod
    def get_target_format_selection(cls):
        return list(cls._TARGET_FORMAT_SELECTION)

    @classmethod
    def detect_source_format(cls, filename):
        lower = (filename or "").strip().lower()
        if lower.endswith(".tex"):
            return "latex"
        if lower.endswith(".typ") or lower.endswith(".typst"):
            return "typst"
        if lower.endswith(".md") or lower.endswith(".markdown"):
            return "markdown"
        if lower.endswith(".html") or lower.endswith(".htm"):
            return "html"
        if lower.endswith(".csv"):
            return "csv"
        if lower.endswith(".xlsx"):
            return "xlsx"
        if lower.endswith(".xls"):
            return "xls"
        if lower.endswith(".pdf"):
            return "pdf"
        if lower.endswith(".txt") or lower.endswith(".rst"):
            return "text"
        return "unknown"

    @classmethod
    def escape_latex(cls, text):
        mapping = {
            "\\": r"\textbackslash{}",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
        }
        return "".join(mapping.get(char, char) for char in str(text or ""))

    @classmethod
    def escape_typst(cls, text):
        mapping = {
            "\\": r"\\",
            "#": r"\#",
            "$": r"\$",
            "[": r"\[",
            "]": r"\]",
            "<": r"\<",
            ">": r"\>",
            "*": r"\*",
            "_": r"\_",
        }
        return "".join(mapping.get(char, char) for char in str(text or ""))

    @classmethod
    def plain_text_to_latex(cls, text, title="Documento"):
        body_lines = []
        for line in (text or "").splitlines():
            line = line.strip()
            if not line:
                body_lines.append(r"\par")
            else:
                body_lines.append(cls.escape_latex(line) + r"\\")
        body = "\n".join(body_lines).strip() or r"\par"
        return (
            "\\documentclass[12pt,a4paper]{article}\n"
            "\\usepackage[T1]{fontenc}\n"
            "\\usepackage[utf8]{inputenc}\n"
            "\\usepackage[brazil]{babel}\n"
            "\\usepackage{lmodern}\n"
            "\\usepackage{geometry}\n"
            "\\geometry{margin=2.5cm}\n"
            "\\begin{document}\n"
            f"\\section*{{{cls.escape_latex(title or 'Documento')}}}\n"
            f"{body}\n"
            "\\end{document}\n"
        )

    @classmethod
    def plain_text_to_typst(cls, text, title="Documento"):
        paragraphs = []
        for block in re.split(r"\n\s*\n", text or ""):
            normalized = " ".join(line.strip() for line in block.splitlines() if line.strip())
            if normalized:
                paragraphs.append(cls.escape_typst(normalized))
        body = "\n\n".join(paragraphs).strip() or cls.escape_typst(title or "Documento")
        heading = cls.escape_typst(title or "Documento")
        return f"= {heading}\n\n{body}\n"

    @classmethod
    def plain_text_to_html(cls, text, title="Documento"):
        body = []
        for block in re.split(r"\n\s*\n", text or ""):
            lines = [html.escape(line.strip()) for line in block.splitlines() if line.strip()]
            if lines:
                body.append(f"<p>{'<br/>'.join(lines)}</p>")
        rendered = "\n".join(body) or "<p></p>"
        return f"<h2>{html.escape(title or 'Documento')}</h2>\n{rendered}"

    @classmethod
    def multiline_text_to_latex(cls, text):
        lines = []
        for line in (text or "").splitlines():
            line = line.strip()
            if not line:
                lines.append(r"\par")
            else:
                lines.append(cls.escape_latex(line) + r"\\")
        return "\n".join(lines).strip() or ""

    @classmethod
    def plain_text_from_html(cls, html_text, preserve_linebreaks=False):
        text = html_text or ""
        replacements = [
            (r"(?i)<br\s*/?>", "\n"),
            (r"(?i)</p>", "\n"),
            (r"(?i)</div>", "\n"),
            (r"(?i)</li>", "\n"),
            (r"(?i)</tr>", "\n"),
            (r"(?i)</h[1-6]>", "\n"),
        ]
        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text)
        text = cls._HTML_TAG_RE.sub(" ", text)
        text = html.unescape(text)
        if preserve_linebreaks:
            text = re.sub(r"[ \t]+\n", "\n", text)
            text = re.sub(r"\n[ \t]+", "\n", text)
            text = re.sub(r"\n{3,}", "\n\n", text)
            return text.strip()
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def plain_text_from_markdown(cls, markdown_text):
        lines = []
        for line in (markdown_text or "").splitlines():
            cleaned = line.rstrip()
            cleaned = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", cleaned)
            cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
            cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
            cleaned = re.sub(r"(\*\*|__)(.*?)\1", r"\2", cleaned)
            cleaned = re.sub(r"(\*|_)(.*?)\1", r"\2", cleaned)
            cleaned = cleaned.replace("|", " | ")
            cleaned = cls._MARKDOWN_PREFIX_RE.sub("", cleaned)
            lines.append(cleaned)
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @classmethod
    def plain_text_from_latex(cls, latex_text):
        text = re.sub(r"(?m)^\s*%.*$", "", latex_text or "")
        text = text.replace(r"\par", "\n\n")
        text = text.replace(r"\\", "\n")
        text = cls._LATEX_COMMAND_RE.sub(" ", text)
        text = re.sub(r"[{}]", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return re.sub(r"[ \t]+", " ", text).strip()

    @classmethod
    def plain_text_from_typst(cls, typst_text):
        lines = []
        for line in (typst_text or "").splitlines():
            cleaned = re.sub(r"//.*$", "", line).strip()
            if not cleaned:
                lines.append("")
                continue
            cleaned = re.sub(r"^\s*=+\s*", "", cleaned)
            cleaned = cleaned.replace("[", " ").replace("]", " ")
            cleaned = cls._TYPST_COMMAND_RE.sub(" ", cleaned)
            cleaned = cleaned.replace("#", " ")
            lines.append(cleaned)
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return re.sub(r"[ \t]+", " ", text).strip()

    @classmethod
    def normalize_plain_text_to_format(cls, text, target_format, title="Documento"):
        if target_format == "latex":
            return cls.plain_text_to_latex(text, title=title)
        if target_format == "typst":
            return cls.plain_text_to_typst(text, title=title)
        if target_format == "html":
            return cls.plain_text_to_html(text, title=title)
        raise UserError(f"Formato de destino não suportado: {target_format}")

    @classmethod
    def latex_from_page_content(cls, html_content, title="Documento"):
        payload = cls.extract_template_source_from_page_content(
            html_content,
            title=title,
            target_format="latex",
        )
        return payload["normalized_source"]

    @classmethod
    def extract_template_source_from_page_content(cls, html_content, title="Documento", target_format="latex"):
        raw_html = html_content or ""
        plain = cls.plain_text_from_html(raw_html, preserve_linebreaks=True)
        if not plain:
            return {
                "normalized_source": "",
                "native_source_text": raw_html,
                "native_format": "html",
                "source_filename": "",
                "parser_used": "knowledge_page_empty",
                "latex_source": "",
                "typst_source": "",
                "html_source": raw_html,
            }
        latex_source = (
            plain
            if any(marker in plain for marker in (r"\documentclass", r"\begin{document}", "{{"))
            else cls.plain_text_to_latex(plain, title=title)
        )
        typst_source = cls.plain_text_to_typst(plain, title=title)
        html_source = raw_html or cls.plain_text_to_html(plain, title=title)
        normalized_source = {
            "latex": latex_source,
            "typst": typst_source,
            "html": html_source,
        }.get(target_format, latex_source)
        return {
            "normalized_source": normalized_source,
            "native_source_text": raw_html,
            "native_format": "html",
            "source_filename": "",
            "parser_used": "knowledge_page",
            "latex_source": latex_source,
            "typst_source": typst_source,
            "html_source": html_source,
        }

    @classmethod
    def extract_placeholders(cls, text):
        seen = set()
        keys = []
        for match in cls._PLACEHOLDER_RE.finditer(text or ""):
            key = match.group(1)
            if key not in seen:
                seen.add(key)
                keys.append(key)
        return keys

    @classmethod
    def build_inferred_parameter_spec(cls, text, default_phase=0, reserved_keys=None):
        reserved = set(reserved_keys or [])
        items = [
            {
                "key": key,
                "type": "string",
                "label": key.replace("_", " ").strip().capitalize(),
                "fase": default_phase or 0,
            }
            for key in cls.extract_placeholders(text)
            if key not in reserved
        ]
        if not items:
            return ""
        return json.dumps({"optional": items}, ensure_ascii=False, indent=2)

    @classmethod
    def _decode_binary_text(cls, binary_data):
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return binary_data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return binary_data.decode("utf-8", errors="ignore")

    @classmethod
    def _csv_rows_from_text(cls, text):
        stream = io.StringIO(text or "")
        return [row for row in csv.reader(stream) if any((cell or "").strip() for cell in row)]

    @classmethod
    def _col_ref_to_index(cls, cell_ref):
        letters = "".join(char for char in (cell_ref or "") if char.isalpha()).upper()
        index = 0
        for char in letters:
            index = (index * 26) + (ord(char) - 64)
        return max(index - 1, 0)

    @classmethod
    def _extract_xlsx_shared_strings(cls, archive):
        try:
            xml_data = archive.read("xl/sharedStrings.xml")
        except KeyError:
            return []
        root = ET.fromstring(xml_data)
        strings = []
        for item in root.findall("main:si", cls._XLSX_NS):
            texts = [node.text or "" for node in item.findall(".//main:t", cls._XLSX_NS)]
            strings.append("".join(texts))
        return strings

    @classmethod
    def _extract_xlsx_sheet_paths(cls, archive):
        try:
            workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
            rel_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        except KeyError:
            return []
        rel_map = {}
        for rel in rel_root.findall("pkgrel:Relationship", cls._XLSX_NS):
            rel_id = rel.attrib.get("Id")
            target = rel.attrib.get("Target", "")
            if rel_id:
                rel_map[rel_id] = target
        sheet_entries = []
        for index, sheet in enumerate(workbook_root.findall("main:sheets/main:sheet", cls._XLSX_NS), start=1):
            rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = rel_map.get(rel_id, f"worksheets/sheet{index}.xml")
            target = target.lstrip("/")
            if not target.startswith("xl/"):
                target = f"xl/{target}"
            sheet_entries.append((sheet.attrib.get("name") or f"Planilha {index}", target))
        return sheet_entries

    @classmethod
    def _extract_xlsx_rows(cls, binary_data):
        workbook = []
        with zipfile.ZipFile(io.BytesIO(binary_data)) as archive:
            shared_strings = cls._extract_xlsx_shared_strings(archive)
            sheet_entries = cls._extract_xlsx_sheet_paths(archive)
            if not sheet_entries:
                sheet_entries = [("Planilha 1", "xl/worksheets/sheet1.xml")]
            for sheet_name, sheet_path in sheet_entries:
                try:
                    root = ET.fromstring(archive.read(sheet_path))
                except KeyError:
                    continue
                rows = []
                for row_node in root.findall(".//main:sheetData/main:row", cls._XLSX_NS):
                    indexed = {}
                    for cell in row_node.findall("main:c", cls._XLSX_NS):
                        ref = cell.attrib.get("r", "")
                        cell_type = cell.attrib.get("t", "")
                        col_index = cls._col_ref_to_index(ref)
                        value = ""
                        if cell_type == "inlineStr":
                            value = "".join(
                                node.text or ""
                                for node in cell.findall(".//main:is//main:t", cls._XLSX_NS)
                            )
                        else:
                            node = cell.find("main:v", cls._XLSX_NS)
                            value = node.text or "" if node is not None else ""
                            if cell_type == "s" and value.isdigit():
                                shared_index = int(value)
                                if shared_index < len(shared_strings):
                                    value = shared_strings[shared_index]
                        indexed[col_index] = value
                    if not indexed:
                        continue
                    max_index = max(indexed.keys())
                    row = [indexed.get(index, "") for index in range(max_index + 1)]
                    while row and not (row[-1] or "").strip():
                        row.pop()
                    if row:
                        rows.append(row)
                if rows:
                    workbook.append((sheet_name, rows))
        return workbook

    @classmethod
    def _extract_xls_rows(cls, binary_data):
        try:
            import xlrd
        except Exception as exc:
            raise UserError(
                "Arquivo XLS exige suporte Python adicional (xlrd) ou parser externo configurado."
            ) from exc
        workbook = xlrd.open_workbook(file_contents=binary_data)
        sheets = []
        for sheet in workbook.sheets():
            rows = []
            for row_index in range(sheet.nrows):
                row = [str(sheet.cell_value(row_index, col_index) or "") for col_index in range(sheet.ncols)]
                while row and not row[-1].strip():
                    row.pop()
                if row:
                    rows.append(row)
            if rows:
                sheets.append((sheet.name or "Planilha", rows))
        return sheets

    @classmethod
    def _rows_to_plain_text(cls, sheet_rows):
        blocks = []
        for sheet_name, rows in sheet_rows:
            lines = [f"[{sheet_name}]"]
            for row in rows:
                lines.append(" | ".join((cell or "").strip() for cell in row))
            blocks.append("\n".join(lines).strip())
        return "\n\n".join(blocks).strip()

    @classmethod
    def _latex_column_spec(cls, column_count):
        return "|" + "|".join(["p{3.2cm}"] * max(column_count, 1)) + "|"

    @classmethod
    def _rows_to_latex_document(cls, sheet_rows, title):
        body = [
            "\\documentclass[12pt,a4paper]{article}",
            "\\usepackage[T1]{fontenc}",
            "\\usepackage[utf8]{inputenc}",
            "\\usepackage[brazil]{babel}",
            "\\usepackage{lmodern}",
            "\\usepackage{geometry}",
            "\\usepackage{longtable}",
            "\\geometry{margin=2.5cm}",
            "\\begin{document}",
            f"\\section*{{{cls.escape_latex(title or 'Documento')}}}",
        ]
        for sheet_name, rows in sheet_rows:
            if not rows:
                continue
            column_count = max(len(row) for row in rows)
            body.append(f"\\subsection*{{{cls.escape_latex(sheet_name)}}}")
            body.append(f"\\begin{{longtable}}{{{cls._latex_column_spec(column_count)}}}")
            for row in rows:
                normalized = list(row) + [""] * (column_count - len(row))
                escaped = [cls.escape_latex(cell) for cell in normalized]
                body.append(" & ".join(escaped) + r" \\ \hline")
            body.append("\\end{longtable}")
        body.append("\\end{document}")
        return "\n".join(body) + "\n"

    @classmethod
    def _rows_to_typst_document(cls, sheet_rows, title):
        blocks = [f"= {cls.escape_typst(title or 'Documento')}"]
        for sheet_name, rows in sheet_rows:
            if not rows:
                continue
            column_count = max(len(row) for row in rows)
            blocks.append(f"\n== {cls.escape_typst(sheet_name)}")
            blocks.append(f"#table(columns: {column_count},")
            cells = []
            for row in rows:
                normalized = list(row) + [""] * (column_count - len(row))
                cells.extend(f"  [{cls.escape_typst(cell)}]," for cell in normalized)
            blocks.extend(cells)
            blocks.append(")")
        return "\n".join(blocks).strip() + "\n"

    @classmethod
    def _rows_to_html_document(cls, sheet_rows, title):
        blocks = [f"<h2>{html.escape(title or 'Documento')}</h2>"]
        for sheet_name, rows in sheet_rows:
            if not rows:
                continue
            blocks.append(f"<h3>{html.escape(sheet_name)}</h3>")
            blocks.append("<table class='table table-sm table-bordered'>")
            for row in rows:
                blocks.append("<tr>")
                for cell in row:
                    blocks.append(f"<td>{html.escape(cell or '')}</td>")
                blocks.append("</tr>")
            blocks.append("</table>")
        return "\n".join(blocks)

    @classmethod
    def _best_effort_plain_text(cls, binary_data, source_format):
        if source_format == "html":
            return cls.plain_text_from_html(cls._decode_binary_text(binary_data), preserve_linebreaks=True)
        if source_format == "markdown":
            return cls.plain_text_from_markdown(cls._decode_binary_text(binary_data))
        if source_format == "latex":
            return cls.plain_text_from_latex(cls._decode_binary_text(binary_data))
        if source_format == "typst":
            return cls.plain_text_from_typst(cls._decode_binary_text(binary_data))
        return cls._decode_binary_text(binary_data).strip()

    @classmethod
    def extract_template_source_from_upload(cls, env, upload_file, upload_filename, target_format="latex"):
        if not upload_file:
            return {
                "normalized_source": "",
                "native_source_text": "",
                "native_format": "unknown",
                "source_filename": upload_filename or "",
                "parser_used": False,
                "latex_source": "",
                "typst_source": "",
                "html_source": "",
            }

        try:
            binary = base64.b64decode(upload_file)
        except Exception as exc:
            raise UserError(f"Falha ao decodificar upload: {exc}") from exc

        filename = upload_filename or "documento"
        source_format = cls.detect_source_format(filename)
        parser = env.get("gov.ai.ml.lexoid.parser")

        if source_format in {"pdf", "xls"} and parser and target_format in {"latex", "typst", "html"}:
            parsed = parser.parse_upload_to_latex(upload_file, filename)
            latex_source = (parsed or {}).get("latex", "")
            parser_used = (parsed or {}).get("parser_used")
            plain = cls.plain_text_from_latex(latex_source)
            typst_source = cls.plain_text_to_typst(plain, title=filename)
            html_source = cls.plain_text_to_html(plain, title=filename)
            normalized_source = {
                "latex": latex_source,
                "typst": typst_source,
                "html": html_source,
            }.get(target_format, latex_source)
            return {
                "normalized_source": normalized_source,
                "native_source_text": plain,
                "native_format": source_format,
                "source_filename": filename,
                "parser_used": parser_used or "lexoid",
                "latex_source": latex_source,
                "typst_source": typst_source,
                "html_source": html_source,
            }

        if source_format == "pdf":
            raise UserError(
                "Upload PDF requer parser externo configurado para extracao estruturada. "
                "Ative o Lexoid ou envie uma fonte textual como LaTeX, Typst, Markdown ou CSV."
            )

        title = filename or "Documento Ingerido"
        native_text = ""
        latex_source = ""
        typst_source = ""
        html_source = ""
        parser_used = False

        if source_format == "latex":
            native_text = cls._decode_binary_text(binary).strip()
            plain = cls.plain_text_from_latex(native_text)
            latex_source = native_text
            typst_source = cls.plain_text_to_typst(plain, title=title)
            html_source = cls.plain_text_to_html(plain, title=title)
        elif source_format == "typst":
            native_text = cls._decode_binary_text(binary).strip()
            plain = cls.plain_text_from_typst(native_text)
            latex_source = cls.plain_text_to_latex(plain, title=title)
            typst_source = native_text
            html_source = cls.plain_text_to_html(plain, title=title)
        elif source_format == "markdown":
            native_text = cls._decode_binary_text(binary).strip()
            plain = cls.plain_text_from_markdown(native_text)
            latex_source = cls.plain_text_to_latex(plain, title=title)
            typst_source = cls.plain_text_to_typst(plain, title=title)
            html_source = cls.plain_text_to_html(plain, title=title)
        elif source_format == "html":
            native_text = cls._decode_binary_text(binary).strip()
            payload = cls.extract_template_source_from_page_content(
                native_text,
                title=title,
                target_format=target_format,
            )
            return {
                **payload,
                "source_filename": filename,
            }
        elif source_format == "csv":
            native_text = cls._decode_binary_text(binary).strip()
            rows = cls._csv_rows_from_text(native_text)
            sheet_rows = [("CSV", rows)] if rows else []
            latex_source = cls._rows_to_latex_document(sheet_rows, title=title)
            typst_source = cls._rows_to_typst_document(sheet_rows, title=title)
            html_source = cls._rows_to_html_document(sheet_rows, title=title)
        elif source_format == "xlsx":
            sheet_rows = cls._extract_xlsx_rows(binary)
            native_text = cls._rows_to_plain_text(sheet_rows)
            latex_source = cls._rows_to_latex_document(sheet_rows, title=title)
            typst_source = cls._rows_to_typst_document(sheet_rows, title=title)
            html_source = cls._rows_to_html_document(sheet_rows, title=title)
            parser_used = "xlsx_local"
        elif source_format == "xls":
            sheet_rows = cls._extract_xls_rows(binary)
            native_text = cls._rows_to_plain_text(sheet_rows)
            latex_source = cls._rows_to_latex_document(sheet_rows, title=title)
            typst_source = cls._rows_to_typst_document(sheet_rows, title=title)
            html_source = cls._rows_to_html_document(sheet_rows, title=title)
            parser_used = "xls_local"
        else:
            native_text = cls._best_effort_plain_text(binary, source_format)
            latex_source = cls.plain_text_to_latex(native_text, title=title)
            typst_source = cls.plain_text_to_typst(native_text, title=title)
            html_source = cls.plain_text_to_html(native_text, title=title)
            if source_format == "pdf":
                parser_used = "fallback_plain_text"

        normalized_source = {
            "latex": latex_source,
            "typst": typst_source,
            "html": html_source,
        }.get(target_format, latex_source)
        return {
            "normalized_source": normalized_source,
            "native_source_text": native_text,
            "native_format": source_format,
            "source_filename": filename,
            "parser_used": parser_used,
            "latex_source": latex_source,
            "typst_source": typst_source,
            "html_source": html_source,
        }

    @classmethod
    def extract_latex_from_upload(cls, env, upload_file, upload_filename):
        payload = cls.extract_template_source_from_upload(
            env,
            upload_file,
            upload_filename,
            target_format="latex",
        )
        return payload.get("latex_source", ""), payload.get("parser_used")
