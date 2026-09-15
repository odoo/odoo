from odoo import _, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleLoyaltyCouponWizard(models.TransientModel):
    _name = "sale.loyalty.coupon.wizard"
    _description = "Sale Loyalty - Apply Coupon Wizard"

    order_id = fields.Many2one(
        comodel_name="sale.order",
        default=lambda self: self.env.context.get("active_id"),
        required=True,
    )

    coupon_code = fields.Char(required=True)

    def action_apply(self):
        self.check_singleton()
        if not self.order_id:
            _debug.logic("coupon_apply_refused", wizard=self, reason="no_order")
            raise ValidationError(_("Invalid sales order."))
        status = self.order_id._try_apply_code(self.coupon_code)
        _debug.lifecycle(
            "coupon_code_tried", order=self.order_id, failed="error" in status
        )
        if "error" in status:
            raise ValidationError(status["error"])
        all_rewards = self.env["loyalty.reward"]
        for rewards in status.values():
            all_rewards |= rewards
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "sale_loyalty.sale_loyalty_reward_wizard_action"
        )
        action["context"] = {
            "active_id": self.order_id.id,
            "default_reward_ids": all_rewards.ids,
        }
        return action
