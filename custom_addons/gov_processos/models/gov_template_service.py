import base64
import html
import json
import re

from odoo.exceptions import UserError


class GovTemplateService:
    _HTML_TAG_RE = re.compile(r"<[^>]+>")
    _PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")

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
    def latex_from_page_content(cls, html_content, title="Documento"):
        plain = cls.plain_text_from_html(html_content, preserve_linebreaks=True)
        if not plain:
            return ""
        if any(marker in plain for marker in (r"\documentclass", r"\begin{document}", "{{")):
            return plain
        return cls.plain_text_to_latex(plain, title=title)

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
    def extract_latex_from_upload(cls, env, upload_file, upload_filename):
        if not upload_file:
            return "", False

        parser = env.get("gov.ai.ml.lexoid.parser")
        if parser:
            result = parser.parse_upload_to_latex(upload_file, upload_filename)
            latex = (result or {}).get("latex", "")
            if latex:
                return latex, (result or {}).get("parser_used")

        try:
            binary = base64.b64decode(upload_file)
            filename = (upload_filename or "").lower()
            if filename.endswith(".tex"):
                try:
                    return binary.decode("utf-8"), "tex_upload"
                except UnicodeDecodeError:
                    return binary.decode("latin-1", errors="ignore"), "tex_upload"
            text = binary.decode("utf-8", errors="ignore").strip()
            latex = cls.plain_text_to_latex(text, title=upload_filename or "Documento Ingerido")
            return latex, "fallback_local"
        except Exception as exc:
            raise UserError(f"Falha ao processar upload em LaTeX: {exc}") from exc
