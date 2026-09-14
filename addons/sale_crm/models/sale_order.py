from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    opportunity_id = fields.Many2one(
        comodel_name="crm.lead",
        index="btree_not_null",
        domain="[('type', '=', 'opportunity'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )

    def action_confirm(self):
        res = super(
            SaleOrder,
            self.with_context(
                {k: v for k, v in self.env.context.items() if k != "default_tag_ids"}
            ),
        ).action_confirm()
        for order in self:
            _debug.pipeline(
                "opportunity_revenue_update",
                order=order,
                opportunity=order.opportunity_id,
            )
            order.opportunity_id._update_revenues_from_so(order)
        return res
