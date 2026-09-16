from odoo import api, fields, models
from odoo.tools.translate import _


class ResPartner(models.Model):
    _inherit = "res.partner"

    user_purchase_id = fields.Many2one(
        comodel_name="res.users",
        string="Buyer",
        compute="_compute_user_purchase_id",
        precompute=True,
        store=True,
        readonly=False,
        tracking=True,
        help="The internal user in charge of purchases from this contact.",
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
    )
    purchase_order_count = fields.Integer(
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

    @api.depends("parent_id")
    def _compute_user_purchase_id(self):
        for partner in self.filtered(
            lambda partner: (
                not partner.user_purchase_id
                and not partner.is_company
                and partner.parent_id.user_purchase_id
            )
        ):
            partner.user_purchase_id = partner.parent_id.user_purchase_id

    def _compute_purchase_order_count(self):
        self._update_order_count(
            "purchase.order",
            "purchase_order_count",
            "purchase.group_purchase_user",
            domain=self._get_purchase_order_domain_count(),
        )

    def _get_application_statistics(self):
        data_list = super()._get_application_statistics()
        return self._add_order_statistics(
            data_list,
            "purchase_order_count",
            "purchase.group_purchase_user",
            "fa-solid fa-credit-card",
            _("Purchases"),
            "o_tag_color_5",
        )

    @api.model
    def _get_purchase_order_domain_count(self):
        return []
