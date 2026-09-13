from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountChangeLockDate(models.TransientModel):
    """Lock date wizard, extended to seed the default report external values."""

    _inherit = "account.change.lock.date"

    @_debug.perf.timed
    def _create_default_report_external_values(self, lock_date_field):
        """Create the default report external values of the period being locked.

        tax_lock_date seeds the tax reports only, while
        max(fiscalyear_lock_date, hard_lock_date) seeds all the other reports.

        :param str lock_date_field: name of the lock date field being set
        """
        # extends account.accountant
        date_from, date_to = self._get_current_period_dates(lock_date_field)
        self.env["account.report"]._create_default_external_values(
            date_from,
            date_to,
            lock_date_field == "tax_lock_date",
            company=self.company_id,
        )
