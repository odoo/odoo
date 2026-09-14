from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import TransactionMemo

RESERVED_TAGS = TransactionMemo(
    "res.partner.tag.reserved", invalidated_by=("res.partner.tag",)
)

_debug = DebugLog(__name__)


class ResPartnerTag(models.Model):
    _inherit = "res.partner.tag"

    order_type = fields.Selection(
        selection=[
            ("sale", "Sale Orders"),
            ("purchase", "Purchase Orders"),
        ],
        string="Order Scope",
        help="Order type whose partner selection this tag restricts. "
        "Leave empty to restrict every order type.",
    )
    group_ids = fields.Many2many(
        comodel_name="res.groups",
        string="Reserved For",
        help="Only users in one of these groups may pick a partner tagged with "
        "this tag, or with one of its children, on an order of the scope "
        "above. Leave empty to place the tag outside the restriction.",
    )

    @api.model
    def _get_domain_partner_allowed(self, order_type):
        memo = RESERVED_TAGS(self.env)
        if order_type not in memo:
            memo[order_type] = (
                self.sudo()
                .search(
                    Domain("group_ids", "!=", False)
                    & Domain("order_type", "in", (False, order_type)),
                )
                .ids
            )
        reserved = self.sudo().browse(memo[order_type])
        if not reserved:
            _debug.logic("partner_tags_unrestricted", order_type=order_type)
            return Domain.TRUE

        user_group_ids = set(self.env.user._get_effective_group_ids())
        allowed = reserved.filtered(
            lambda category: user_group_ids.intersection(category.group_ids.ids),
        )
        if not allowed:
            _debug.logic(
                "partner_tags_all_reserved", order_type=order_type, reserved=reserved
            )
            return Domain.FALSE
        _debug.logic(
            "partner_tags_allowed",
            order_type=order_type,
            reserved=reserved,
            allowed=allowed,
        )
        return Domain("tag_ids", "child_of", allowed.ids)
