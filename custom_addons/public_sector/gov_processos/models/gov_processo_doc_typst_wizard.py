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
    edit_mode = fields.Selection(
        [
            ("structured", "Estruturado"),
            ("manual_typst", "Typst Manual"),
        ],
        string="Modo de Edicao",
        default="structured",
        required=True,
    )
    active_doc_id = fields.Many2one(
        "gov.processo.doc",
        string="Documento Ativo",
        readonly=True,
    )
    active_doc_state = fields.Selection(
        related="active_doc_id.state",
        string="Estado do Documento Ativo",
        readonly=True,
    )
    active_doc_version = fields.Integer(
        related="active_doc_id.version",
        string="Versao do Documento Ativo",
        readonly=True,
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
    typst_source_manual = fields.Text(string="Codigo Typst Completo")
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

    def _build_structured_typst_source(self):
        self.ensure_one()
        return self.typst_preview or GovTypstDocumentBuilder.build_document(self._build_payload())

    def _get_manual_typst_source(self, allow_builder_seed=False):
        self.ensure_one()
        manual_source = self.typst_source_manual or ""
        if manual_source.strip():
            return manual_source
        active_doc = self.active_doc_id.exists()
        if active_doc and (active_doc.typst_source or "").strip():
            return active_doc.typst_source
        if allow_builder_seed:
            return self._build_structured_typst_source()
        return manual_source

    def _get_effective_typst_source(self, allow_builder_seed=False):
        self.ensure_one()
        if self.edit_mode == "manual_typst":
            return self._get_manual_typst_source(allow_builder_seed=allow_builder_seed)
        return self._build_structured_typst_source()

    def _build_snapshot_payload(self):
        self.ensure_one()
        return {
            "wizard_edit_mode": self.edit_mode,
            "payload": self._build_payload(),
            "active_doc_id": self.active_doc_id.id or False,
        }

    def _build_return_to_wizard_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Novo Documento Typst",
            "res_model": "gov.processo.doc.typst.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _prepare_document_vals(self, *, allow_builder_seed=False):
        self.ensure_one()
        typst_source = self._get_effective_typst_source(allow_builder_seed=allow_builder_seed)
        return {
            "processo_id": self.processo_id.id,
            "doc_type": self.doc_type,
            "name": self.name,
            "typst_source": typst_source,
            "latex_source": self.source_doc_id.latex_source if self.source_doc_id else False,
            "render_mode": "manual_source",
            "dados_snapshot": json.dumps(
                self._build_snapshot_payload(),
                ensure_ascii=False,
                indent=2,
            ),
            "dfd_area_requisitante": self.area_requisitante,
            "dfd_objeto": self.objeto,
            "dfd_justificativa": self.justificativa,
        }

    def _get_changed_document_vals(self, doc, vals):
        self.ensure_one()
        changed_vals = {}
        for field_name, value in vals.items():
            if doc[field_name] != value:
                changed_vals[field_name] = value
        return changed_vals

    def _ensure_active_document(self, *, allow_builder_seed=False):
        self.ensure_one()
        vals = self._prepare_document_vals(allow_builder_seed=allow_builder_seed)
        doc = self.active_doc_id.exists()
        if doc:
            if doc.state == "assinado":
                raise UserError("O documento ativo ja esta assinado e nao pode ser reutilizado.")
            changed_vals = self._get_changed_document_vals(doc, vals)
            if changed_vals:
                changed_vals["change_reason"] = "Documento ativo sincronizado pelo wizard Typst"
                doc.write(changed_vals)
        else:
            doc = self.env["gov.processo.doc"].create(vals)
            self.active_doc_id = doc.id
        return doc

    def _validate_wizard_inputs(self):
        self.ensure_one()
        missing = []
        if not self.processo_id:
            missing.append("Processo")
        if not self.doc_type:
            missing.append("Tipo de Documento")
        if not (self.name or "").strip():
            missing.append("Nome do Documento")
        if self.edit_mode == "manual_typst":
            if not (self._get_manual_typst_source() or "").strip():
                missing.append("Codigo Typst Completo")
        else:
            if not self.modelo_typst:
                missing.append("Modelo Typst")
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
            if wizard.edit_mode == "manual_typst":
                raise UserError("A previa automatica esta disponivel apenas no modo estruturado.")
            wizard._validate_wizard_inputs()
            wizard.typst_preview = wizard._build_structured_typst_source()
        return {
            "type": "ir.actions.act_window",
            "res_model": "gov.processo.doc.typst.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_abrir_builder(self):
        self.ensure_one()
        if not self.processo_id:
            raise UserError("Selecione um processo antes de abrir o builder.")
        if not self.doc_type:
            raise UserError("Informe o tipo do documento antes de abrir o builder.")
        if not (self.name or "").strip():
            raise UserError("Informe o nome do documento antes de abrir o builder.")
        doc = self._ensure_active_document(allow_builder_seed=True)
        self.active_doc_id = doc.id
        return doc._build_construtor_visual_action(
            initial_mode="typst",
            extra_params={
                "return_action": self._build_return_to_wizard_action(),
            },
        )

    def action_abrir_documento_ativo(self):
        self.ensure_one()
        doc = self.active_doc_id.exists()
        if not doc:
            raise UserError("Nenhum documento ativo foi criado ainda.")
        return {
            "type": "ir.actions.act_window",
            "name": doc.name,
            "res_model": "gov.processo.doc",
            "res_id": doc.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_sincronizar_do_documento_ativo(self):
        self.ensure_one()
        doc = self.active_doc_id.exists()
        if not doc:
            raise UserError("Nenhum documento ativo foi criado ainda.")
        self.typst_source_manual = doc.typst_source or ""
        if self.edit_mode == "structured":
            self.typst_preview = doc.typst_source or ""
        return self._build_return_to_wizard_action()

    def action_criar_documento(self):
        self.ensure_one()
        self._validate_wizard_inputs()
        doc = self._ensure_active_document()
        self.active_doc_id = doc.id
        if self.gerar_pdf_imediatamente:
            doc.action_gerar_pdf()
        return {
            "type": "ir.actions.act_window",
            "res_model": "gov.processo.doc",
            "res_id": doc.id,
            "view_mode": "form",
            "target": "current",
        }
