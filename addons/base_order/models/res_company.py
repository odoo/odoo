from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools.date_utils import get_timedelta, time_unit_selection
from odoo.tools.translate import _

_debug = DebugLog(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    order_cycle_count = fields.Integer(
        string="Order Cycle",
        default=3,
        help="How long a partner may go without ordering before it counts as "
        "having gone quiet. Ordering rhythms differ by company and by "
        "industry: a seasonal crop supplier may need twelve months where a "
        "convenience retailer needs one.",
    )
    order_cycle_unit = fields.Selection(
        selection=time_unit_selection("day", "week", "month", "year"),
        default="month",
        required=True,
    )

    @api.constrains("order_cycle_count")
    def _check_order_cycle_count(self):
        for company in self:
            if company.order_cycle_count < 0:
                _debug.logic(
                    "order_cycle_rejected",
                    company=company,
                    count=company.order_cycle_count,
                )
                raise ValidationError(
                    _(
                        "The order cycle of %(company)s must be zero or more.",
                        company=company.display_name,
                    ),
                )

    def _get_order_cycle_cutoff_date(self):
        self.check_singleton()
        _debug.logic(
            "order_cycle_cutoff",
            company=self,
            count=self.order_cycle_count,
            unit=self.order_cycle_unit,
        )
        return fields.Date.today() - get_timedelta(
            self.order_cycle_count, self.order_cycle_unit
        )
