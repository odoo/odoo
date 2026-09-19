from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    sale_order_ids = fields.One2many(
        comodel_name="sale.order",
        inverse_name="partner_id",
        string="Sales Order",
    )
    sale_order_count = fields.Integer(
        compute="_compute_sale_order_count",
        groups="sale.group_sale_salesman",
    )
    sale_warn_msg = fields.Text(string="Message for Sales Order")

    def _compute_sale_order_count(self):
        self._update_order_count(
            "sale.order",
            "sale_order_count",
            "sale.group_sale_salesman",
            domain=self._get_sale_order_domain_count(),
        )

    def _get_application_statistics(self):
        data_list = super()._get_application_statistics()
        return self._add_order_statistics(
            data_list,
            "sale_order_count",
            "sale.group_sale_salesman",
            "fa-solid fa-dollar-sign",
            self.env._("Sale Orders"),
            "o_tag_color_2",
        )

    def _compute_credit_to_invoice(self):
        super()._compute_credit_to_invoice()

        if not (commercial_partners := self.commercial_partner_id & self):
            _debug.logic("credit_to_invoice_skipped", reason="no_commercial_partner")
            return

        company = self.env.company

        if not company.account_config_id.account_use_credit_limit:
            _debug.logic("credit_to_invoice_skipped", reason="credit_limit_disabled")
            return

        sale_orders = self.env["sale.order"].search(
            [
                ("company_id", "=", company.id),
                (
                    "partner_invoice_id",
                    "any",
                    [
                        ("commercial_partner_id", "in", commercial_partners.ids),
                    ],
                ),
                ("line_ids", "any", [("amount_taxexc_to_invoice", ">", 0)]),
                ("state", "=", "done"),
            ],
        )
        for (partner, currency), orders in sale_orders.grouped(
            lambda so: (so.partner_invoice_id, so.currency_id),
        ).items():
            amount_to_invoice_sum = sum(orders.mapped("amount_taxexc_to_invoice"))
            credit_company_currency = currency._convert(
                amount_to_invoice_sum,
                company.currency_id,
                company,
                fields.Date.context_today(self),
            )
            partner.commercial_partner_id.credit_to_invoice += credit_company_currency
            _debug.logic(
                "credit_to_invoice",
                partner=partner,
                orders=orders,
                amount=credit_company_currency,
            )

    @api.model
    def _get_sale_order_domain_count(self):
        return []

    @api.model
    def _get_order_activity_sources(self):
        return super()._get_order_activity_sources() + [
            ("sale.order", [("state", "=", "done")]),
        ]

    def _has_order(self, partner_domain):
        self.check_singleton()
        sale_order = (
            self.env["sale.order"]
            .sudo()
            .search(
                Domain.AND(
                    [
                        partner_domain,
                        [
                            ("state", "=", "done"),
                        ],
                    ],
                ),
                limit=1,
            )
        )
        _debug.perf.count("partner_has_order", partner=self, found=bool(sale_order))
        return bool(sale_order)

    def _can_edit_country(self):
        return super()._can_edit_country() and not self._has_order(
            [
                "|",
                ("partner_invoice_id", "=", self.id),
                ("partner_id", "=", self.id),
            ],
        )

    def can_edit_vat(self):
        return super().can_edit_vat() and not self._has_order(
            [("partner_id", "child_of", self.commercial_partner_id.id)],
        )
