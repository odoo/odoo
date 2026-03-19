import base64
import io
import importlib
import json
import logging
import re
import urllib.error
import urllib.request
import zipfile

from odoo import api, models


_logger = logging.getLogger(__name__)


class GovAiMlLexoidParser(models.AbstractModel):
    _name = "gov.ai.ml.lexoid.parser"
    _description = "Parser de Upload para LaTeX (Lexoid)"

    @api.model
    def _escape_latex(self, text):
        if not text:
            return ""
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
        return "".join(mapping.get(char, char) for char in str(text))

    @api.model
    def _plain_text_to_latex(self, text, title="Documento"):
        escaped_title = self._escape_latex(title or "Documento")
        body_lines = []
        for line in (text or "").splitlines():
            line = line.strip()
            if not line:
                body_lines.append(r"\par")
            else:
                body_lines.append(self._escape_latex(line) + r"\\")
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
            f"\\section*{{{escaped_title}}}\n"
            f"{body}\n"
            "\\end{document}\n"
        )

    @api.model
    def _extract_plain_text_fallback(self, binary_data, filename):
        filename = (filename or "").lower()
        if filename.endswith(".docx"):
            with zipfile.ZipFile(io.BytesIO(binary_data)) as archive:
                xml_data = archive.read("word/document.xml").decode("utf-8", errors="ignore")
            xml_data = re.sub(r"</w:p>", "\n", xml_data)
            text = re.sub(r"<[^>]+>", " ", xml_data)
            return re.sub(r"\s+\n", "\n", re.sub(r"[ \t]+", " ", text)).strip()
        return binary_data.decode("utf-8", errors="ignore").strip()

    @api.model
    def _normalize_lexoid_result(self, result):
        if isinstance(result, str):
            return result.strip()
        if isinstance(result, dict):
            for key in ("latex", "latex_source", "content", "result"):
                value = result.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return ""

    @api.model
    def _parse_with_lexoid_python(self, binary_data, filename):
        try:
            lexoid = importlib.import_module("lexoid")
        except Exception:
            return ""

        candidates = (
            ("parse_to_latex", {"content": binary_data, "filename": filename or ""}),
            ("parse_upload_to_latex", {"content": binary_data, "filename": filename or ""}),
            ("parse", {"content": binary_data, "filename": filename or "", "output_format": "latex"}),
        )
        for func_name, kwargs in candidates:
            func = getattr(lexoid, func_name, None)
            if not callable(func):
                continue
            try:
                latex = self._normalize_lexoid_result(func(**kwargs))
                if latex:
                    return latex
            except TypeError:
                try:
                    latex = self._normalize_lexoid_result(func(binary_data, filename or ""))
                    if latex:
                        return latex
                except Exception:
                    continue
            except Exception:
                continue
        return ""

    @api.model
    def _parse_with_lexoid(self, binary_data, filename):
        latex_python = self._parse_with_lexoid_python(binary_data, filename)
        if latex_python:
            return latex_python

        icp = self.env["ir.config_parameter"].sudo()
        endpoint = (icp.get_param("gov_ai_ml.lexoid_endpoint") or "").strip()
        if not endpoint:
            return ""
        api_key = (icp.get_param("gov_ai_ml.lexoid_api_key") or "").strip()
        timeout = int(icp.get_param("gov_ai_ml.lexoid_timeout_seconds") or 45)

        payload = {
            "filename": filename or "",
            "content_base64": base64.b64encode(binary_data).decode("ascii"),
            "output_format": "latex",
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            _logger.warning("Falha no parser Lexoid para %s: %s", filename or "arquivo", exc)
            return ""

        try:
            parsed = json.loads(raw)
            return self._normalize_lexoid_result(parsed)
        except json.JSONDecodeError:
            return raw.strip()

    @api.model
    def parse_upload_to_latex(self, upload_file_b64, filename=None):
        if not upload_file_b64:
            return {"latex": "", "parser_used": False}
        binary_data = base64.b64decode(upload_file_b64)

        latex = self._parse_with_lexoid(binary_data, filename)
        if latex:
            return {"latex": latex, "parser_used": "lexoid"}

        text = self._extract_plain_text_fallback(binary_data, filename or "")
        return {
            "latex": self._plain_text_to_latex(text, title=filename or "Documento Ingerido"),
            "parser_used": "fallback_local",
        }
