from odoo import fields, models


class GovDocumentVersion(models.Model):
    """Armazena snapshots versionados do documento concreto em edição."""

    _name = "gov.document.version"
    _description = "Versão de Documento"
    _order = "version_no desc"

    document_instance_id = fields.Many2one(
        "gov.document.instance",
        required=True,
        ondelete="cascade",
        string="Documento",
    )
    version_no = fields.Integer(string="Versão", required=True)
    layout_json = fields.Text(string="Layout (JSON)")
    resolved_context_json = fields.Text(string="Contexto Resolvido (JSON)")
    dynamic_namespaces_json = fields.Text(string="Namespaces Dinâmicos")
    typst_source = fields.Text(string="Fonte Typst")
    typst_hash = fields.Char(string="Hash do Typst")
    change_summary = fields.Char(string="Resumo da Mudança")
    edited_by = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        readonly=True,
        string="Editado por",
    )
    created_at = fields.Datetime(
        default=fields.Datetime.now,
        readonly=True,
        string="Criado em",
    )
    is_major = fields.Boolean(
        default=False,
        string="Versão Principal",
    )

    def action_rerender(self):
        renderer = self.env["gov.document.typst.renderer"]
        for rec in self:
            rec.write({"typst_source": renderer.render_version(rec)})
        return True
