from odoo import fields, models

class SpreadsheetCellThread(models.Model):
    _inherit = "spreadsheet.cell.thread"

    document_id = fields.Many2one("documents.document", readonly=True, ondelete="cascade")
    template_id = fields.Many2one("spreadsheet.template", readonly=True, ondelete="cascade")

    def _get_spreadsheet_record(self):
        return super()._get_spreadsheet_record() or self.document_id or self.template_id
