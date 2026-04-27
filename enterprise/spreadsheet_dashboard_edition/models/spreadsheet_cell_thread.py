from odoo import fields, models

class SpreadsheetCellThread(models.Model):
    _inherit = "spreadsheet.cell.thread"

    dashboard_id = fields.Many2one("spreadsheet.dashboard", readonly=True, ondelete="cascade")

    def _get_spreadsheet_record(self):
        return super()._get_spreadsheet_record() or self.dashboard_id
