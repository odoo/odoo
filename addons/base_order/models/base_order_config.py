from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools.date_utils import time_unit_selection

_debug = DebugLog(__name__)


class BaseOrderConfig(models.Model):
    _name = "base_order.config"
    _description = "A company's base order configuration"
    _inherit = ["mixin.company.config"]

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
                    self.env._(
                        "The order cycle of %(company)s must be zero or more.",
                        company=company.company_id.display_name,
                    ),
                )
