from odoo import fields, models


class GovDocumentVersion(models.Model):
    """Armazena snapshots versionados de uma instância documental."""

    _name = "gov.document.version"
    _description = "Versão do Documento Administrativo"
    _order = "version_no desc, id desc"

    document_id = fields.Many2one(
        "gov.document.instance",
        required=True,
        ondelete="cascade",
        string="Documento",
    )
    version_no = fields.Integer(string="Versão", required=True)
    summary = fields.Char(string="Resumo")
    snapshot_layout_json = fields.Text(string="Snapshot do Layout (JSON)")
    snapshot_resolved_context_json = fields.Text(
        string="Snapshot do Contexto Resolvido (JSON)"
    )
    snapshot_typst_source = fields.Text(string="Snapshot da Fonte Typst")
    snapshot_typst_hash = fields.Char(string="Snapshot do Hash Typst")
    snapshot_state = fields.Char(string="Estado do Documento")
    snapshot_legal_date = fields.Date(string="Data do Snapshot Jurídico")
