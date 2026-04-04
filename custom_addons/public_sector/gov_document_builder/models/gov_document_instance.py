import json

from odoo import fields, models


class GovDocumentInstance(models.Model):
    """Representa o documento administrativo concreto em edição e versionamento."""

    _name = "gov.document.instance"
    _description = "Instância de Documento Administrativo"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Nome do Documento", required=True)
    document_type_id = fields.Many2one(
        "gov.document.type",
        required=True,
        string="Tipo Documental",
    )
    template_id = fields.Many2one("gov.document.template", string="Template")
    process_id = fields.Many2one(
        "gov.processo",
        string="Processo",
        ondelete="cascade",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Rascunho"),
            ("in_review", "Em Revisão"),
            ("approved", "Aprovado"),
            ("archived", "Arquivado"),
        ],
        default="draft",
        string="Estado",
        tracking=True,
    )
    layout_json = fields.Text(string="Layout Canônico (JSON)")
    resolved_context_json = fields.Text(
        string="Contexto Resolvido (JSON)",
        readonly=True,
    )
    typst_source = fields.Text(string="Fonte Typst", readonly=True)
    typst_hash = fields.Char(string="Hash do Typst", readonly=True)
    compiled_at = fields.Datetime(readonly=True)
    current_version_no = fields.Integer(default=1, string="Versão Atual")
    owner_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        string="Responsável",
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Unidade Demandante",
    )
    legal_snapshot_date = fields.Date(string="Data do Snapshot Jurídico")
    version_ids = fields.One2many(
        "gov.document.version",
        "document_instance_id",
        string="Versões",
    )
    version_count = fields.Integer(
        compute="_compute_version_count",
        string="Total de Versões",
    )

    def _compute_version_count(self):
        Version = self.env["gov.document.version"]
        for rec in self:
            rec.version_count = Version.search_count([("document_instance_id", "=", rec.id)])

    def get_layout(self):
        self.ensure_one()
        return json.loads(self.layout_json or "[]")

    def set_layout(self, nodes_list):
        self.ensure_one()
        self.layout_json = json.dumps(nodes_list, ensure_ascii=False)

    def action_approve(self):
        for rec in self:
            rec.state = "approved"
            rec._create_version("Aprovação")
        return True

    def action_archive(self):
        self.write({"state": "archived"})
        return True

    def _create_version(self, summary=""):
        Version = self.env["gov.document.version"]
        created_versions = self.env["gov.document.version"]
        for rec in self:
            existing_version_nos = rec.version_ids.mapped("version_no")
            base_version_no = (rec.current_version_no or 1) - 1
            version_no = max(existing_version_nos, default=base_version_no) + 1
            created_versions |= Version.create(
                {
                    "document_instance_id": rec.id,
                    "version_no": version_no,
                    "layout_json": rec.layout_json or "[]",
                    "resolved_context_json": rec.resolved_context_json or "{}",
                    "typst_source": rec.typst_source or False,
                    "typst_hash": rec.typst_hash or False,
                    "change_summary": summary,
                }
            )
            rec.current_version_no = version_no
        return created_versions

    def action_open_builder(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "gov_document_builder.instance",
            "context": {
                **self.env.context,
                "document_id": self.id,
            },
        }
