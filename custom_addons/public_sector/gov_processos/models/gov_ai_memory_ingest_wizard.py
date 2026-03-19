from odoo import fields, models
from odoo.exceptions import UserError

from .gov_template_service import GovTemplateService


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

    def _extract_latex_from_upload(self):
        self.ensure_one()
        return GovTemplateService.extract_latex_from_upload(
            self.env,
            self.upload_file,
            self.upload_filename,
        )

    def _append_manual_section_to_latex(self, latex_source, manual_text):
        source = latex_source or ""
        insert = (
            "\n\n% Notas manuais adicionadas no wizard\n"
            "\\section*{Notas manuais}\n"
            f"{GovTemplateService.escape_latex(manual_text)}\n"
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
