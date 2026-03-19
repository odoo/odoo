from odoo import fields, models
from odoo.tools.sql import column_exists, create_column, table_exists


class GovProcessoVersao(models.Model):
    _name = "gov.processo.versao"
    _description = "Histórico de Versões de Documento"
    _order = "version_number desc"

    def _auto_init(self):
        result = super()._auto_init()
        if table_exists(self.env.cr, "gov_processo_versao") and not column_exists(
            self.env.cr, "gov_processo_versao", "typst_snapshot"
        ):
            create_column(self.env.cr, "gov_processo_versao", "typst_snapshot", "text")
        return result

    doc_id = fields.Many2one(
        "gov.processo.doc",
        required=True,
        ondelete="cascade",
        index=True,
    )
    version_number = fields.Integer(string="Versão", required=True)
    content_snapshot_html = fields.Html(string="Snapshot HTML")
    latex_snapshot = fields.Text(string="Snapshot LaTeX")
    typst_snapshot = fields.Text(string="Snapshot Typst")
    pdf_snapshot = fields.Binary(string="PDF desta versão", attachment=True)
    changed_by = fields.Many2one("res.users", default=lambda self: self.env.user)
    changed_at = fields.Datetime(default=fields.Datetime.now)
    change_reason = fields.Text(string="Motivo da Alteração")
    ai_generated = fields.Boolean(default=False)
    diff_summary = fields.Text(
        string="Resumo das Alterações",
        help="Preenchido pela IA no step 8.x",
    )
