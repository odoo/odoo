import base64
from odoo import fields, models
from odoo.exceptions import UserError


class GovAiMemoryIngestWizard(models.TransientModel):
    _name = "gov.ai.memory.ingest.wizard"
    _description = "Ingestão de Memória IA por UG"

    company_id = fields.Many2one(
        "res.company",
        string="Unidade Gestora",
        required=True,
        default=lambda self: self.env.company,
    )
    name = fields.Char(required=True)
    tags = fields.Char()
    text_input = fields.Text(string="Texto para Memória")
    upload_file = fields.Binary(string="Arquivo para parser (preferência: DOCX/PDF/TXT/MD)")
    upload_filename = fields.Char()

    def _escape_latex(self, text):
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

    def _plain_text_to_latex(self, text, title="Documento"):
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
            f"\\section*{{{self._escape_latex(title or 'Documento')}}}\n"
            f"{body}\n"
            "\\end{document}\n"
        )

    def _extract_latex_from_upload(self):
        self.ensure_one()
        if not self.upload_file:
            return "", False

        parser = self.env.get("gov.ai.ml.lexoid.parser")
        if parser:
            result = parser.parse_upload_to_latex(self.upload_file, self.upload_filename)
            latex = (result or {}).get("latex", "")
            if latex:
                return latex, (result or {}).get("parser_used")

        try:
            binary = base64.b64decode(self.upload_file)
            text = binary.decode("utf-8", errors="ignore").strip()
            latex = self._plain_text_to_latex(text, title=self.upload_filename or "Documento Ingerido")
            return latex, "fallback_local"
        except Exception as exc:
            raise UserError(f"Falha ao processar upload em LaTeX: {exc}") from exc

    def _append_manual_section_to_latex(self, latex_source, manual_text):
        source = latex_source or ""
        insert = (
            "\n\n% Notas manuais adicionadas no wizard\n"
            "\\section*{Notas manuais}\n"
            f"{self._escape_latex(manual_text)}\n"
        )
        marker = "\\end{document}"
        if marker in source:
            return source.replace(marker, insert + marker, 1)
        return source + insert

    def action_ingest(self):
        self.ensure_one()
        text_manual = (self.text_input or "").strip()
        latex_upload, parser_used = self._extract_latex_from_upload()

        text = text_manual
        if latex_upload:
            text = latex_upload
            if text_manual:
                text = self._append_manual_section_to_latex(text, text_manual)
        if not text:
            raise UserError("Informe texto manual ou arquivo para ingestão.")

        tags = (self.tags or "").strip()
        if parser_used:
            tag_parser = f"parser:{parser_used}"
            tags = f"{tags}, {tag_parser}".strip(", ").strip() if tags else tag_parser

        memory = self.env["gov.ai.memory"].create(
            {
                "name": self.name,
                "company_id": self.company_id.id,
                "source_type": "upload" if self.upload_file else "manual",
                "content_text": text,
                "tags": tags,
                "upload_file": self.upload_file,
                "upload_filename": self.upload_filename,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "gov.ai.memory",
            "res_id": memory.id,
            "view_mode": "form",
            "target": "current",
        }
