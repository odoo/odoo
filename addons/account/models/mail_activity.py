from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MailActivity(models.Model):
    _inherit = "mail.activity"

    @_debug.perf.timed
    def action_view_document(self):
        # OVERRIDE
        # when opening the "View all activities", and opening a return, we actually want the kanban view of return checks
        _debug.lifecycle("action_view_document", records=self)
        if self.res_model != "account.return":
            return super().action_view_document()

        return (
            self.env["account.return"].browse(self.res_id).action_view_account_return()
        )
