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

    @api.depends("price_reduce", "product_id", "product_id.taxes_id")
    def _compute_price_reduce_taxinc(self):
        for event in self:
            # sudo necessary here since the field is most probably accessed through the website
            tax_ids = event.product_id.taxes_id.filtered_domain(
                self.env["account.tax"]._check_company_domain(event.event_id.company_id)
            )
            taxes = tax_ids.compute_all(
                event.price_reduce,
                event.event_id.company_id.currency_id,
                1.0,
                product=event.product_id,
            )
            event.price_reduce_taxinc = taxes["total_included"]

    @api.depends("product_id", "product_id.taxes_id", "price")
    def _compute_price_incl(self):
        for event in self:
            if event.product_id and event.price:
                tax_ids = event.product_id.taxes_id.filtered_domain(
                    self.env["account.tax"]._check_company_domain(
                        event.event_id.company_id
                    )
                )
                taxes = tax_ids.compute_all(
                    event.price, event.currency_id, 1.0, product=event.product_id
                )
                event.price_incl = taxes["total_included"]
            else:
                event.price_incl = 0
