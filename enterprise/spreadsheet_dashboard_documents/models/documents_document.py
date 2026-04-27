from odoo import models

class Document(models.Model):
    _inherit = "documents.document"

    def join_spreadsheet_session(self, access_token=None):
        data = super().join_spreadsheet_session(access_token)
        return dict(data, can_add_to_dashboard=self.env['spreadsheet.dashboard'].has_access('create'))
