from odoo import api, fields, models
from odoo.exceptions import UserError

from ..services.gov_typst_document_builder import GovTypstDocumentBuilder


class GovProcessoDocTypstWizard(models.TransientModel):
    _name = "gov.processo.doc.typst.wizard"
    _description = "Wizard de Criacao de Documento Typst"

    processo_id = fields.Many2one(
        "gov.processo",
        string="Processo",
        required=True,
        readonly=True,
    )
    modelo_typst = fields.Selection(
        selection=lambda self: GovTypstDocumentBuilder.get_model_selection(),
        string="Modelo Typst",
        required=True,
        default="nota_tecnica",
    )
    doc_type = fields.Selection(
        selection=lambda self: self.env["gov.processo.doc"]._fields["doc_type"].selection,
        string="Tipo de Documento",
        required=True,
        default="outro",
    )
    name = fields.Char(string="Nome do Documento", required=True)
    titulo = fields.Char(string="Titulo", required=True)
    subtitulo = fields.Char(string="Subtitulo")
    referencia = fields.Char(string="Referencia")
    base_legal = fields.Text(string="Base Legal")
    area_requisitante = fields.Char(string="Area Requisitante")
    objeto = fields.Text(string="Objeto", required=True)
    justificativa = fields.Text(string="Justificativa")
    fatos_relevantes = fields.Text(string="Fatos Relevantes")
    pontos_chave = fields.Text(
        string="Pontos-Chave",
        help="Um item por linha. O wizard renderiza como lista.",
    )
    quadro_resumo = fields.Text(
        string="Quadro Resumo",
        help="Use uma linha por item no formato 'Rotulo: valor'.",
    )
    encaminhamento = fields.Text(string="Encaminhamento")
    observacoes_finais = fields.Text(string="Observacoes Finais")
    assinante_nome = fields.Char(
        string="Assinante",
        default=lambda self: self.env.user.name,
    )
    assinante_cargo = fields.Char(string="Cargo / Funcao")
    incluir_assinatura = fields.Boolean(
        string="Incluir bloco de assinatura",
        default=True,
    )
    gerar_pdf_imediatamente = fields.Boolean(
        string="Gerar PDF apos criar",
        default=False,
    )
    typst_preview = fields.Text(
        string="Previa Typst",
        compute="_compute_typst_preview",
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        processo_id = values.get("processo_id") or self.env.context.get("default_processo_id")
        if not processo_id:
            return values
        processo = self.env["gov.processo"].browse(processo_id).exists()
        if not processo:
            return values
        defaults = self._get_default_values_for_model(
            model_key=values.get("modelo_typst") or self.env.context.get("default_modelo_typst") or "nota_tecnica",
            processo=processo,
        )
        for key, value in defaults.items():
            if key in fields_list and not values.get(key):
                values[key] = value
        return values

    @api.onchange("modelo_typst")
    def _onchange_modelo_typst(self):
        for wizard in self:
            if not wizard.processo_id:
                continue
            defaults = wizard._get_default_values_for_model(wizard.modelo_typst, wizard.processo_id)
            wizard.doc_type = defaults["doc_type"]
            wizard.titulo = defaults["titulo"]
            wizard.subtitulo = defaults["subtitulo"]
            wizard.base_legal = defaults["base_legal"]
            wizard.name = defaults["name"]

    @api.depends(
        "processo_id",
        "modelo_typst",
        "doc_type",
        "name",
        "titulo",
        "subtitulo",
        "referencia",
        "base_legal",
        "area_requisitante",
        "objeto",
        "justificativa",
        "fatos_relevantes",
        "pontos_chave",
        "quadro_resumo",
        "encaminhamento",
        "observacoes_finais",
        "assinante_nome",
        "assinante_cargo",
        "incluir_assinatura",
    )
    def _compute_typst_preview(self):
        for wizard in self:
            if not wizard.processo_id:
                wizard.typst_preview = ""
                continue
            wizard.typst_preview = GovTypstDocumentBuilder.build_document(wizard._build_payload())

    def _get_default_values_for_model(self, model_key, processo):
        defaults = GovTypstDocumentBuilder.get_defaults(model_key)
        title = defaults.get("title") or "Documento"
        return {
            "doc_type": defaults.get("doc_type", "outro"),
            "titulo": title,
            "subtitulo": defaults.get("subtitle") or processo.subject or "",
            "base_legal": defaults.get("legal_basis") or "",
            "referencia": processo.name or "",
            "area_requisitante": "",
            "objeto": processo.subject or "",
            "name": f"{title} - {processo.name or 'Processo'}",
        }

    def _build_payload(self):
        self.ensure_one()
        processo = self.processo_id
        return {
            "model_key": self.modelo_typst,
            "title": self.titulo,
            "subtitle": self.subtitulo,
            "legal_basis": self.base_legal,
            "process_number": processo.name or "",
            "process_subject": processo.subject or "",
            "process_type_label": dict(processo._fields["process_type"].selection).get(
                processo.process_type,
                processo.process_type or "",
            ),
            "process_scope_label": dict(processo._fields["process_scope"].selection).get(
                processo.process_scope,
                processo.process_scope or "",
            ),
            "company_name": processo.ug_id.name or "",
            "reference": self.referencia,
            "requesting_area": self.area_requisitante,
            "responsible_name": processo.responsible_id.name if processo.responsible_id else "",
            "generated_on": fields.Date.today().strftime("%d/%m/%Y"),
            "summary_lines": self.quadro_resumo,
            "object_text": self.objeto,
            "justification_text": self.justificativa,
            "facts_text": self.fatos_relevantes,
            "key_points_text": self.pontos_chave,
            "routing_text": self.encaminhamento,
            "closing_notes": self.observacoes_finais,
            "include_signature": self.incluir_assinatura,
            "signer_name": self.assinante_nome,
            "signer_role": self.assinante_cargo,
        }

    def action_criar_documento(self):
        self.ensure_one()
        if not self.processo_id:
            raise UserError("Selecione um processo antes de criar o documento.")
        typst_source = self.typst_preview or GovTypstDocumentBuilder.build_document(self._build_payload())
        doc = self.env["gov.processo.doc"].create(
            {
                "processo_id": self.processo_id.id,
                "doc_type": self.doc_type,
                "name": self.name,
                "typst_source": typst_source,
                "render_mode": "manual_source",
                "dfd_area_requisitante": self.area_requisitante,
                "dfd_objeto": self.objeto,
                "dfd_justificativa": self.justificativa,
            }
        )
        if self.gerar_pdf_imediatamente:
            doc.action_gerar_pdf()
        return {
            "type": "ir.actions.act_window",
            "res_model": "gov.processo.doc",
            "res_id": doc.id,
            "view_mode": "form",
            "target": "current",
        }
