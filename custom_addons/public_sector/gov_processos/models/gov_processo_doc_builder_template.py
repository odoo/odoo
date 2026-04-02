import json

from odoo import api, fields, models

from .constants import DOC_TYPE_SELECTION, PROCESS_TYPE_SELECTION, TEMPLATE_SCOPE_SELECTION
from .gov_ai_doc_service import GovAiDocService


class GovProcessoDocBuilderTemplate(models.Model):
    _name = "gov.processo.doc.builder.template"
    _description = "Template do Construtor Visual de Documento"
    _order = "sequence, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    doc_type = fields.Selection(
        DOC_TYPE_SELECTION,
        string="Tipo de Documento",
        required=True,
    )
    process_type = fields.Selection(
        PROCESS_TYPE_SELECTION,
        string="Tipo de Processo",
        help="Se vazio, aplica a qualquer tipo de processo.",
    )
    process_scope = fields.Selection(
        TEMPLATE_SCOPE_SELECTION,
        string="Escopo",
        default="all",
        required=True,
    )
    block_payload_json = fields.Text(
        string="Payload de Blocos",
        required=True,
        help="JSON com a estrutura inicial de blocos do construtor.",
    )
    notes = fields.Text(string="Observações")

    @api.model
    def _fallback_payload_by_doc_type(self, doc_type):
        templates = {
            "dfd": [
                {
                    "type": "titulo",
                    "content": {
                        "titulo": "DFD — Formalização de Demanda",
                        "subtitulo": "{{process_subject}}",
                    },
                },
                {"type": "cabecalho_processo", "content": {}},
                {"type": "objeto", "content": {"html": ""}},
                {"type": "justificativa", "content": {"html": ""}},
                {"type": "base_legal", "content": {"html": ""}},
                {"type": "quadro_resumo", "content": {"linhas": ""}},
                {
                    "type": "encaminhamento",
                    "content": {"html": ""},
                },
                {
                    "type": "assinatura",
                    "content": {"nome": "", "cargo": ""},
                },
            ],
            "tr": [
                {
                    "type": "titulo",
                    "content": {
                        "titulo": "Termo de Referência",
                        "subtitulo": "{{process_subject}}",
                    },
                },
                {"type": "cabecalho_processo", "content": {}},
                {"type": "objeto", "content": {"html": ""}},
                {"type": "base_legal", "content": {"html": ""}},
                {
                    "type": "pontos_chave",
                    "content": {
                        "texto": (
                            "Objeto delimitado\n"
                            "Critérios de execução definidos\n"
                            "Fiscalização e aceite previstos"
                        )
                    },
                },
                {
                    "type": "encaminhamento",
                    "content": {"html": ""},
                },
                {
                    "type": "assinatura",
                    "content": {"nome": "", "cargo": ""},
                },
            ],
        }
        return templates.get(
            doc_type,
            [
                {
                    "type": "titulo",
                    "content": {
                        "titulo": "{{doc_type_label}}",
                        "subtitulo": "{{process_subject}}",
                    },
                },
                {"type": "cabecalho_processo", "content": {}},
                {"type": "texto_livre", "content": {"html": "<p>Redija aqui o conteúdo principal.</p>"}},
                {"type": "base_legal", "content": {"html": "<p>{{legal_basis_default}}</p>"}},
                {"type": "encaminhamento", "content": {"html": "<p>{{routing_default}}</p>"}},
                {
                    "type": "assinatura",
                    "content": {
                        "nome": "{{responsible_name}}",
                        "cargo": "{{responsible_role}}",
                    },
                },
            ],
        )

    @api.model
    def _render_placeholders_deep(self, value, context):
        if isinstance(value, str):
            return GovAiDocService.render_placeholders(value, context)
        if isinstance(value, list):
            return [self._render_placeholders_deep(item, context) for item in value]
        if isinstance(value, dict):
            return {
                key: self._render_placeholders_deep(item, context)
                for key, item in value.items()
            }
        return value

    def get_block_payload(self):
        self.ensure_one()
        try:
            payload = json.loads(self.block_payload_json or "[]")
        except json.JSONDecodeError:
            payload = []
        return payload if isinstance(payload, list) else []

    def get_rendered_block_payload(self, context):
        self.ensure_one()
        return self._render_placeholders_deep(self.get_block_payload(), context or {})

    @api.model
    def get_default_for_document(self, doc):
        if not doc:
            return self.browse()
        doc.ensure_one()
        scope = doc.process_scope or "compras"
        candidates = self.search(
            [
                ("active", "=", True),
                ("doc_type", "=", doc.doc_type),
                "|",
                ("process_type", "=", False),
                ("process_type", "=", doc.process_type),
                "|",
                ("process_scope", "=", "all"),
                ("process_scope", "=", scope),
            ],
            order="sequence, id",
        )
        if not candidates and doc.doc_type != "outro":
            candidates = self.search(
                [
                    ("active", "=", True),
                    ("doc_type", "=", "outro"),
                ],
                order="sequence, id",
            )
        if not candidates:
            return self.browse()

        def _score(template):
            return (
                1 if template.doc_type == doc.doc_type else 0,
                1 if template.process_type and template.process_type == doc.process_type else 0,
                1 if template.process_scope == scope else 0,
                1 if template.process_scope == "all" else 0,
                -template.sequence,
                -template.id,
            )

        return sorted(candidates, key=_score, reverse=True)[0]

    @api.model
    def get_rendered_payload_for_document(self, doc, context):
        template = self.get_default_for_document(doc)
        if template:
            payload = template.get_rendered_block_payload(context)
            if payload:
                return {
                    "template": template,
                    "blocks": payload,
                }
        payload = self._render_placeholders_deep(
            self._fallback_payload_by_doc_type(doc.doc_type),
            context or {},
        )
        return {
            "template": self.browse(),
            "blocks": payload,
        }
