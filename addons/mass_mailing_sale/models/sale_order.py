from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"
    _mailing_enabled = True

    def _mailing_get_default_domain(self, mailing):
        """Exclude by default canceled orders when performing a mass mailing."""
        _debug.logic("mailing_domain", model=self._name, mailing=mailing)
        return [("state", "!=", "cancel")]
