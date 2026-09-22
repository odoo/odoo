from odoo import api, fields, models

from odoo.addons.product.models.product_template import PRICE_CONTEXT_KEYS


class EventEventTicket(models.Model):
    _inherit = "event.event.ticket"
    _order = "event_id, sequence, price, name, id"

    price_reduce_taxinc = fields.Float(
        string="Price Reduce Tax inc",
        compute="_compute_price_reduce_taxinc",
        compute_sudo=True,
    )
    # Display-only: website_event_sale renders it through t-field and nothing
    # writes it. readonly=False advertised it to the web client as editable
    # while, being a non-stored compute with no inverse, it silently dropped
    # whatever was written. Dropping the kwarg stops the client offering it;
    # a programmatic write() is still discarded without error, which is how
    # the ORM treats every compute without an inverse.
    price_incl = fields.Float(
        string="Price include",
        min_display_digits="Product Price",
        compute="_compute_price_incl",
        compute_sudo=True,
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

        The two tax computes below differ only in the amount they hand to
        compute_all; everything else was the same six lines twice.

        `currency` is the tax jurisdiction's currency -- the event company's --
        for both callers. price_incl used to round in the product's currency
        instead, which is company_id.currency_id or the MAIN company's when the
        product has no company, so a product shared across companies rounded the
        two figures of one ticket in two different currencies while the website
        rendered them side by side.
        """
        self.check_singleton()
        # sudo necessary here since the field is most probably accessed through the website
        taxes = self.product_id.taxes_id.filtered_domain(
            self.env["account.tax"]._check_company_domain(self.event_id.company_id)
        )
        return taxes.compute_all(amount, currency, 1.0, product=self.product_id)[
            "total_included"
        ]

    # price_reduce is contextual (see event.type.ticket._compute_price_reduce), so
    # the pricelist has to be part of this field's cache key too -- without it the
    # ORM hands back whichever pricelist's value was computed first.
    @api.depends_context(*PRICE_CONTEXT_KEYS)
    @api.depends(
        "price_reduce", "product_id", "product_id.taxes_id", "event_id.company_id"
    )
    def _compute_price_reduce_taxinc(self):
        for ticket in self:
            ticket.price_reduce_taxinc = ticket._tax_included(
                ticket.price_reduce, ticket.event_id.company_id.currency_id
            )

    @api.depends("product_id", "product_id.taxes_id", "price", "event_id.company_id")
    def _compute_price_incl(self):
        for ticket in self:
            if ticket.product_id and ticket.price:
                ticket.price_incl = ticket._tax_included(
                    ticket.price, ticket.event_id.company_id.currency_id
                )
            else:
                ticket.price_incl = 0
