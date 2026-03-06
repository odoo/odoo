from odoo import fields, models


class GovProcessoVersao(models.Model):
    _name = "gov.processo.versao"
    _description = "Histórico de Versões de Documento"
    _order = "version_number desc"

    doc_id = fields.Many2one(
        "gov.processo.doc",
        required=True,
        ondelete="cascade",
        index=True,
    )
    version_number = fields.Integer(string="Versão", required=True)
    content_snapshot_html = fields.Html(string="Snapshot HTML")
    latex_snapshot = fields.Text(string="Snapshot LaTeX")
    pdf_snapshot = fields.Binary(string="PDF desta versão", attachment=True)
    changed_by = fields.Many2one("res.users", default=lambda self: self.env.user)
    changed_at = fields.Datetime(default=fields.Datetime.now)
    change_reason = fields.Text(string="Motivo da Alteração")
    ai_generated = fields.Boolean(default=False)
    diff_summary = fields.Text(
        string="Resumo das Alterações",
        help="Preenchido pela IA no step 8.x",
    )
