from odoo import models

class Document(models.Model):
    _inherit = "documents.document"

    def join_spreadsheet_session(self, share_id=None, access_token=None):
        data = super().join_spreadsheet_session(share_id, access_token)
        return dict(data, can_add_to_dashboard=self.env['spreadsheet.dashboard'].check_access_rights('create', raise_exception=False))
