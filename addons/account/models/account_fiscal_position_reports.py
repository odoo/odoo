from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    @_debug.perf.timed
    def action_create_foreign_taxes(self):
        # EXTENDS account
        _debug.lifecycle("action_create_foreign_taxes", records=self)
        super().action_create_foreign_taxes()
        self.env["account.return.type"]._sync_all_returns(self.company_id.root_id)
