from odoo import api, fields, models
from odoo.fields import Domain


class ResPartner(models.Model):
    _inherit = "res.partner"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    sale_order_ids = fields.One2many(
        comodel_name="sale.order",
        inverse_name="partner_id",
        string="Sales Order",
    )
    sale_order_count = fields.Integer(
        string="Sale Order Count",
        compute="_compute_sale_order_count",
        groups="sales_team.group_sale_salesman",
    )
    sale_warn_msg = fields.Text(string="Message for Sales Order")

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    def _compute_sale_order_count(self):
        self.sale_order_count = 0
        if not self.env.user.has_group("sales_team.group_sale_salesman"):
            return

        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search_fetch(
            [("id", "child_of", self.ids)],
            ["parent_id"],
        )
        sale_order_groups = self.env["sale.order"]._read_group(
            domain=Domain.AND(
                [
                    self._get_sale_order_domain_count(),
                    [("partner_id", "in", all_partners.ids)],
                ],
            ),
            groupby=["partner_id"],
            aggregates=["__count"],
        )
        self_ids = set(self._ids)

        for partner, count in sale_order_groups:
            while partner:
                if partner.id in self_ids:
                    partner.sale_order_count += count
                partner = partner.parent_id

    def _compute_application_statistics_hook(self):
        data_list = super()._compute_application_statistics_hook()
        if not self.env.user.has_group("sales_team.group_sale_salesman"):
            return data_list
        for partner in self.filtered("sale_order_count"):
            data_list[partner.id].append(
                {
                    "iconClass": "fa-usd",
                    "value": partner.sale_order_count,
                    "label": self.env._("Sale Orders"),
                    "tagClass": "o_tag_color_2",
                }
            )
        return data_list

    def _compute_credit_to_invoice(self):
        # EXTENDS 'account'
        super()._compute_credit_to_invoice()

        if not (commercial_partners := self.commercial_partner_id & self):
            return  # nothing to compute

        company = self.env.company

        if not company.account_use_credit_limit:
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

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    @api.model
    def _get_sale_order_domain_count(self):
        return []

    # ------------------------------------------------------------
    # VALIDATIONS
    # ------------------------------------------------------------

    def _has_order(self, partner_domain):
        self.ensure_one()
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
        return bool(sale_order)

    def _can_edit_country(self):
        """Can't edit `country_id` if there is (non draft) issued SO."""
        return super()._can_edit_country() and not self._has_order(
            [
                "|",
                ("partner_invoice_id", "=", self.id),
                ("partner_id", "=", self.id),
            ],
        )

    def can_edit_vat(self):
        """Can't edit `vat` if there is (non draft) issued SO."""
        return super().can_edit_vat() and not self._has_order(
            [("partner_id", "child_of", self.commercial_partner_id.id)],
        )
