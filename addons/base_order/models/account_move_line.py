from odoo import fields, models
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_downpayment = fields.Boolean()

    def _get_fields_order_line_link(self):
        return []

    def _copy_data_extend_business_fields(self, values):
        super()._copy_data_extend_business_fields(values)
        linked = self.sudo()
        for field_name in self._get_fields_order_line_link():
            values[field_name] = [Command.set(linked[field_name].ids)]

    def _related_analytic_distribution(self):
        vals = super()._related_analytic_distribution()
        linked = self.sudo()
        for field_name in self._get_fields_order_line_link():
            if order_lines := linked[field_name]:
                vals |= order_lines[0].analytic_distribution or {}
                _debug.logic(
                    "analytic_from_order_line", line=self, order_line=order_lines[0]
                )
        return vals

    def _compute_warn_msg_from_product(self, field_name, group):
        has_warning_group = self.env.user.has_group(group)
        _debug.logic(
            "product_warn_msg", lines=self, field=field_name, shown=has_warning_group
        )
        for line in self:
            line[field_name] = line.product_id[field_name] if has_warning_group else ""
