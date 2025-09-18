from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools.translate import _


class ResPartner(models.Model):
    _inherit = "res.partner"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    user_purchase_id = fields.Many2one(
        comodel_name="res.users",
        string="Buyer",
    )
    property_purchase_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Supplier Currency",
        company_dependent=True,
        help="This currency will be used for purchases from the current partner",
    )
    purchase_order_ids = fields.One2many(
        comodel_name="purchase.order",
        inverse_name="partner_id",
        string="Purchase Order",
    )
    purchase_order_count = fields.Integer(
        string="Purchase Order Count",
        compute="_compute_purchase_order_count",
        groups="purchase.group_purchase_user",
    )
    purchase_warn_msg = fields.Text(string="Message for Purchase Order")
    receipt_reminder_email = fields.Boolean(
        string="Receipt Reminder",
        company_dependent=True,
        help="Automatically send a confirmation email to the vendor X days before the expected receipt date, asking him to confirm the exact date.",
    )
    reminder_date_before_receipt = fields.Integer(
        string="Days Before Receipt",
        company_dependent=True,
        help="Number of days to send reminder email before the promised receipt date",
    )

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    def _compute_purchase_order_count(self):
        self.purchase_order_count = 0
        if not self.env.user._has_group("purchase.group_purchase_user"):
            return

        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search_fetch(
            [("id", "child_of", self.ids)],
            ["parent_id"],
        )
        purchase_order_groups = self.env["purchase.order"]._read_group(
            domain=Domain.AND(
                [
                    self._get_purchase_order_domain_count(),
                    [("partner_id", "in", all_partners.ids)],
                ],
            ),
            groupby=["partner_id"],
            aggregates=["__count"],
        )
        self_ids = set(self._ids)

        for partner, count in purchase_order_groups:
            while partner:
                if partner.id in self_ids:
                    partner.purchase_order_count += count
                partner = partner.parent_id

    def _compute_application_statistics_hook(self):
        data_list = super()._compute_application_statistics_hook()
        if not self.env.user.has_group("purchase.group_purchase_user"):
            return data_list
        for partner in self.filtered(lambda partner: partner.purchase_order_count):
            stat_info = {
                "iconClass": "fa-credit-card",
                "value": partner.purchase_order_count,
                "label": _("Purchases"),
                "tagClass": "o_tag_color_5",
            }
            data_list[partner.id].append(stat_info)
        return data_list

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    @api.model
    def _get_purchase_order_domain_count(self):
        return []
