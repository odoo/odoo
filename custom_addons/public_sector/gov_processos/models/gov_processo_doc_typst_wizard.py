import html
import json
import re

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..services.gov_typst_document_builder import GovTypstDocumentBuilder
from ..services.gov_typst_framework import GovTypstFramework


class GovProcessoDocTypstWizard(models.TransientModel):
    _name = "gov.processo.doc.typst.wizard"
    _description = "Wizard de Criacao de Documento Typst"
    _HTML_TAG_RE = re.compile(r"<[^>]+>")

    processo_id = fields.Many2one(
        "gov.processo",
        string="Processo",
        readonly=True,
    )
    source_doc_id = fields.Many2one(
        "gov.processo.doc",
        string="Documento Base",
        readonly=True,
    )
    modelo_typst = fields.Selection(
        selection=lambda self: GovTypstDocumentBuilder.get_model_selection(),
        string="Modelo Typst",
        default="nota_tecnica",
    )
    incluir_peca_dfd = fields.Boolean(string="Peca DFD")
    incluir_peca_justificativa = fields.Boolean(string="Peca Justificativa")
    incluir_peca_etp = fields.Boolean(string="Peca ETP")
    incluir_peca_tr = fields.Boolean(string="Peca TR")
    incluir_peca_despacho = fields.Boolean(string="Peca Despacho")
    incluir_peca_ratificacao = fields.Boolean(string="Peca Ratificacao")
    incluir_peca_nota_tecnica = fields.Boolean(string="Peca Nota Tecnica")
    doc_type = fields.Selection(
        selection=lambda self: self.env["gov.processo.doc"]._fields["doc_type"].selection,
        string="Tipo de Documento",
        default="outro",
    )
    name = fields.Char(string="Nome do Documento")
    titulo = fields.Char(string="Titulo")
    subtitulo = fields.Char(string="Subtitulo")
    referencia = fields.Char(string="Referencia")
    base_legal = fields.Text(string="Base Legal")
    area_requisitante = fields.Char(string="Area Requisitante")
    objeto = fields.Text(string="Objeto")
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
        default=True,
    )
    typst_preview = fields.Text(
        string="Previa Typst",
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
        source_doc = self._get_reference_doc(processo)
        if source_doc and "source_doc_id" in fields_list:
            values["source_doc_id"] = source_doc.id
        defaults = self._get_default_values_for_model(
            model_key=values.get("modelo_typst") or self.env.context.get("default_modelo_typst") or "nota_tecnica",
            processo=processo,
            source_doc=source_doc,
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
            defaults = wizard._get_default_values_for_model(
                wizard.modelo_typst,
                wizard.processo_id,
                source_doc=wizard.source_doc_id,
            )
            wizard.doc_type = defaults["doc_type"]
            wizard.titulo = defaults["titulo"]
            wizard.subtitulo = defaults["subtitulo"]
            wizard.base_legal = defaults["base_legal"]
            wizard.name = defaults["name"]
            wizard._apply_piece_defaults(wizard.modelo_typst)
            if not wizard.area_requisitante:
                wizard.area_requisitante = defaults["area_requisitante"]
            if not wizard.objeto:
                wizard.objeto = defaults["objeto"]
            if not wizard.justificativa:
                wizard.justificativa = defaults["justificativa"]

    def _get_reference_doc(self, processo):
        docs = self.env["gov.processo.doc"].search(
            [("processo_id", "=", processo.id)],
            order="id desc",
            limit=10,
        )
        for doc in docs:
            if doc.pdf_file or doc.latex_source or doc.typst_source or doc.content_html:
                return doc
        return docs[:1]

    def _html_to_text(self, value):
        text = self._HTML_TAG_RE.sub(" ", value or "")
        return re.sub(r"\s+", " ", html.unescape(text)).strip()

    def _get_default_values_for_model(self, model_key, processo, source_doc=None):
        defaults = GovTypstDocumentBuilder.get_defaults(model_key)
        title = defaults.get("title") or "Documento"
        source_objeto = ""
        source_justificativa = ""
        source_area = ""
        if source_doc:
            source_area = source_doc.dfd_area_requisitante or ""
            source_objeto = self._html_to_text(source_doc.dfd_objeto or "")
            source_justificativa = self._html_to_text(source_doc.dfd_justificativa or "")
        values = {
            "doc_type": defaults.get("doc_type", "outro"),
            "titulo": title,
            "subtitulo": defaults.get("subtitle") or processo.subject or "",
            "base_legal": defaults.get("legal_basis") or "",
            "referencia": source_doc.name if source_doc else (processo.name or ""),
            "area_requisitante": source_area,
            "objeto": source_objeto or processo.subject or "",
            "justificativa": source_justificativa,
            "name": f"{title} - {processo.name or 'Processo'}",
        }
        for piece_key in GovTypstFramework.get_piece_keys(model_key):
            values[f"incluir_peca_{piece_key}"] = True
        return values

    def _apply_piece_defaults(self, model_key):
        self.ensure_one()
        selected_piece_keys = set(GovTypstFramework.get_piece_keys(model_key))
        for piece_key, _label in GovTypstFramework.get_piece_selection():
            setattr(self, f"incluir_peca_{piece_key}", piece_key in selected_piece_keys)

    def _get_selected_piece_keys(self):
        self.ensure_one()
        selected = []
        for piece_key, _label in GovTypstFramework.get_piece_selection():
            if getattr(self, f"incluir_peca_{piece_key}"):
                selected.append(piece_key)
        return selected

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
            "piece_keys": self._get_selected_piece_keys(),
        }

    def _validate_wizard_inputs(self):
        self.ensure_one()
        missing = []
        if not self.processo_id:
            missing.append("Processo")
        if not self.modelo_typst:
            missing.append("Modelo Typst")
        if not self.doc_type:
            missing.append("Tipo de Documento")
        if not (self.name or "").strip():
            missing.append("Nome do Documento")
        if not (self.titulo or "").strip():
            missing.append("Titulo")
        if not (self.objeto or "").strip():
            missing.append("Objeto")
        if not self._get_selected_piece_keys():
            missing.append("Pecas do documento")
        if missing:
            raise UserError(
                "Preencha os campos obrigatorios antes de criar o documento: "
                + ", ".join(missing)
            )

    def action_atualizar_previa(self):
        for wizard in self:
            wizard._validate_wizard_inputs()
            wizard.typst_preview = GovTypstDocumentBuilder.build_document(wizard._build_payload())
        return {
            "type": "ir.actions.act_window",
            "res_model": "gov.processo.doc.typst.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_criar_documento(self):
        self.ensure_one()
        self._validate_wizard_inputs()
        typst_source = self.typst_preview or GovTypstDocumentBuilder.build_document(self._build_payload())
        doc = self.env["gov.processo.doc"].create(
            {
                "processo_id": self.processo_id.id,
                "doc_type": self.doc_type,
                "name": self.name,
                "typst_source": typst_source,
                "latex_source": self.source_doc_id.latex_source if self.source_doc_id else False,
                "render_mode": "manual_source",
                "dados_snapshot": json.dumps(self._build_payload(), ensure_ascii=False, indent=2),
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
