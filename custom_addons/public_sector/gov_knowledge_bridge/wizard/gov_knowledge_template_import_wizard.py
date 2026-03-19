from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.gov_processos.models.constants import (
    DOC_TYPE_SELECTION,
    PROCESS_TYPE_SELECTION,
    TEMPLATE_SCOPE_SELECTION,
)
from odoo.addons.gov_processos.models.gov_template_service import GovTemplateService


class GovKnowledgeTemplateImportWizard(models.TransientModel):
    _name = "gov.knowledge.template.import.wizard"
    _description = "Importação de Modelo GOV a partir do Knowledge"

    article_id = fields.Many2one(
        "document.page",
        string="Artigo Knowledge",
        required=True,
        readonly=True,
    )
    template_id = fields.Many2one(
        "gov.ai.template",
        string="Atualizar Modelo Existente",
        domain="[('knowledge_article_id', '=', article_id)]",
    )
    name = fields.Char(string="Nome do Modelo", required=True)
    process_type = fields.Selection(
        PROCESS_TYPE_SELECTION,
        string="Tipo de Processo",
        required=True,
        default="compras_servicos",
    )
    process_scope = fields.Selection(
        TEMPLATE_SCOPE_SELECTION,
        string="Escopo",
        required=True,
        default="all",
    )
    doc_type = fields.Selection(
        DOC_TYPE_SELECTION,
        string="Tipo de Documento",
        required=True,
        default="dfd",
    )
    fase = fields.Integer(string="Fase", default=0, required=True)
    output_format = fields.Selection(
        selection=lambda self: GovTemplateService.get_target_format_selection(),
        string="Saída",
        default="latex",
        required=True,
    )
    source_mode = fields.Selection(
        [
            ("upload", "Upload"),
            ("page_content", "Conteúdo do Artigo"),
        ],
        string="Origem do Modelo",
        default="upload",
        required=True,
    )
    upload_file = fields.Binary(string="Arquivo do Modelo")
    upload_filename = fields.Char()
    source_document = fields.Char(string="Documento de Origem")
    versao_normativa = fields.Char(string="Base Normativa")
    guidance_text = fields.Text(string="Orientações")
    parameter_spec_json = fields.Text(string="Parâmetros (JSON)")
    option_catalog_json = fields.Text(string="Catálogo de Opções (JSON)")
    prompt_system = fields.Text(string="Prompt Sistema")
    prompt_user_tpl = fields.Text(string="Prompt Usuário")

    def _get_template_source(self):
        self.ensure_one()
        if self.source_mode == "page_content":
            payload = GovTemplateService.extract_template_source_from_page_content(
                self.article_id.content,
                title=self.article_id.name,
                target_format=self.output_format,
            )
            if not payload["normalized_source"]:
                raise UserError("O artigo Knowledge não possui conteúdo suficiente para gerar um modelo.")
            return payload

        if not self.upload_file:
            raise UserError("Envie um arquivo para importar o modelo.")
        return GovTemplateService.extract_template_source_from_upload(
            self.env,
            self.upload_file,
            self.upload_filename,
            target_format=self.output_format,
        )

    def action_import(self):
        self.ensure_one()
        source_payload = self._get_template_source()
        template_source = source_payload.get("normalized_source") or ""
        parser_used = source_payload.get("parser_used")
        parameter_spec = (self.parameter_spec_json or "").strip()
        if not parameter_spec:
            parameter_spec = GovTemplateService.build_inferred_parameter_spec(
                template_source,
                default_phase=self.fase,
                reserved_keys=self.env["gov.ai.template"]._BUILTIN_CONTEXT_KEYS,
            )

        vals = {
            "name": self.name,
            "knowledge_article_id": self.article_id.id,
            "process_type": self.process_type,
            "process_scope": self.process_scope,
            "doc_type": self.doc_type,
            "fase": self.fase,
            "output_format": self.output_format,
            "source_document": self.source_document or self.upload_filename or self.article_id.name,
            "source_filename": source_payload.get("source_filename") or self.upload_filename or self.article_id.name,
            "source_input_format": source_payload.get("native_format") or "unknown",
            "source_native_text": source_payload.get("native_source_text") or "",
            "versao_normativa": self.versao_normativa,
            "guidance_text": self.guidance_text,
            "parameter_spec_json": parameter_spec,
            "option_catalog_json": self.option_catalog_json,
            "prompt_system": self.prompt_system,
            "prompt_user_tpl": self.prompt_user_tpl,
            "latex_template": source_payload.get("latex_source") or "",
            "typst_template": source_payload.get("typst_source") or "",
            "active": True,
        }
        if parser_used:
            guidance = (vals.get("guidance_text") or "").strip()
            parser_note = f"Modelo importado via Knowledge ({parser_used})."
            vals["guidance_text"] = (
                f"{guidance}\n\n{parser_note}".strip() if guidance else parser_note
            )

        if self.template_id:
            self.template_id.write(vals)
            template = self.template_id
        else:
            template = self.env["gov.ai.template"].create(vals)

        return {
            "type": "ir.actions.act_window",
            "name": f"Modelo GOV - {template.name}",
            "res_model": "gov.ai.template",
            "res_id": template.id,
            "view_mode": "form",
            "target": "current",
        }
