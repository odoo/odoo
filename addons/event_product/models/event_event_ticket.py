from odoo import api, fields, models


class EventEventTicket(models.Model):
    _inherit = "event.event.ticket"
    _order = "event_id, sequence, price, name, id"

    price_reduce_taxinc = fields.Float(
        string="Price Reduce Tax inc",
        compute="_compute_price_reduce_taxinc",
        compute_sudo=True,
    )
    price_incl = fields.Float(
        string="Price include",
        min_display_digits="Product Price",
        compute="_compute_price_incl",
        compute_sudo=True,
        readonly=False,
    )

    @api.depends("product_id.active")
    def _compute_sale_available(self):
        inactive_product_tickets = self.filtered(
            lambda ticket: not ticket.product_id.active
        )
        for ticket in inactive_product_tickets:
            ticket.sale_available = False
        super(
            EventEventTicket, self - inactive_product_tickets
        )._compute_sale_available()

    def _tax_included(self, amount, currency):
        """`amount` with this ticket's product taxes applied, rounded in `currency`.

        The two tax computes below differ only in the amount and the currency
        they hand to compute_all; everything else was the same six lines twice.
        """
        self.check_singleton()
        # sudo necessary here since the field is most probably accessed through the website
        taxes = self.product_id.taxes_id.filtered_domain(
            self.env["account.tax"]._check_company_domain(self.event_id.company_id)
        )
        return taxes.compute_all(amount, currency, 1.0, product=self.product_id)[
            "total_included"
        ]

    @api.depends("price_reduce", "product_id", "product_id.taxes_id")
    def _compute_price_reduce_taxinc(self):
        for ticket in self:
            ticket.price_reduce_taxinc = ticket._tax_included(
                ticket.price_reduce, ticket.event_id.company_id.currency_id
            )

    @api.depends("product_id", "product_id.taxes_id", "price")
    def _compute_price_incl(self):
        for ticket in self:
            if ticket.product_id and ticket.price:
                ticket.price_incl = ticket._tax_included(
                    ticket.price, ticket.currency_id
                )
            else:
                ticket.price_incl = 0
