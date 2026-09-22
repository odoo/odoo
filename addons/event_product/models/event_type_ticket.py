import logging

from odoo import api, fields, models

from odoo.addons.event_product.models.product_product import (
    raise_event_ticket_service_tracking_error,
)
from odoo.addons.product.models.product_template import PRICE_CONTEXT_KEYS

_logger = logging.getLogger(__name__)


class EventTypeTicket(models.Model):
    _inherit = "event.type.ticket"
    _order = "sequence, price, name, id"

    def _default_product_id(self):
        return self.env.ref(
            "event_product.product_product_event", raise_if_not_found=False
        )

    description = fields.Text(
        compute="_compute_description",
        store=True,
        readonly=False,
    )
    # product
    product_id = fields.Many2one(
        comodel_name="product.product",
        default=_default_product_id,
        index=True,
        required=True,
        domain=[("service_tracking", "=", "event")],
    )
    currency_id = fields.Many2one(
        related="product_id.currency_id",
        string="Currency",
    )
    price = fields.Float(
        min_display_digits="Product Price",
        compute="_compute_price",
        store=True,
        readonly=False,
    )
    price_reduce = fields.Float(
        min_display_digits="Product Price",
        compute="_compute_price_reduce",
        compute_sudo=True,
    )

    @api.constrains("product_id")
    def _check_event_ticket_service_tracking(self):
        # The field-level domain=[("service_tracking", "=", "event")] above only
        # guards the UI/onchange path; a create()/write() via server action, RPC,
        # or another module bypassing the view can still set product_id to a
        # mismatched product. product.product's own
        # _check_event_ticket_service_tracking is keyed off event.event.ticket
        # (a different model), so it cannot cover this model-level gap.
        for ticket in self:
            if ticket.product_id and ticket.product_id.service_tracking != "event":
                raise_event_ticket_service_tracking_error(ticket.product_id)

    @api.depends("product_id")
    def _compute_price(self):
        # Asymmetric on purpose: switching to a product with a nonzero
        # lst_price makes `price` follow it, but switching to a product whose
        # lst_price is falsy (0) leaves an already-set nonzero `price`
        # untouched instead of zeroing it out. This protects a manually
        # overridden/discounted price from being silently clobbered by a
        # product change; it also means the two directions don't mirror each
        # other, which can read as a bug if this comment goes missing.
        for ticket in self:
            if ticket.product_id.lst_price:
                ticket.price = ticket.product_id.lst_price

    @api.depends("product_id")
    def _compute_description(self):
        for ticket in self:
            if ticket.product_id and ticket.product_id.description_sale:
                ticket.description = ticket.product_id.description_sale
            # initialize, i.e for embedded tree views
            if not ticket.description:
                ticket.description = False

    # TODO clean this feature in master
    # Feature broken by design, depending on the hacky `_get_contextual_price` field on products
    # context_dependent, core part of the pricelist mess
    # This field usage should be restricted to the UX, and any use in effective
    # price computation should be replaced by clear calls to the pricelist API
    @api.depends_context(*PRICE_CONTEXT_KEYS)
    @api.depends("product_id", "price")
    def _compute_price_reduce(self):
        for ticket in self:
            contextual_discount = ticket.product_id._get_contextual_discount()
            ticket.price_reduce = (1.0 - contextual_discount) * ticket.price

    def _init_column(self, column_name, *, new_column=False):
        if column_name != "product_id":
            return super()._init_column(column_name, new_column=new_column)

        # fetch void columns
        self.env.cr.execute("SELECT id FROM %s WHERE product_id IS NULL" % self._table)
        # fetchall() yields row tuples [(1,), (2,), ...]; flatten to plain ints
        # so ANY(%s) below adapts to a Postgres integer[] under psycopg3 (a
        # tuple would adapt to a composite "(1)" and fail the integer cast).
        ticket_type_ids = [row[0] for row in self.env.cr.fetchall()]
        if not ticket_type_ids:
            return None

        # update existing columns
        _logger.debug(
            "Table '%s': setting default value of new column %s to unique values for each row",
            self._table,
            column_name,
        )
        default_event_product = self.env.ref(
            "event_product.product_product_event", raise_if_not_found=False
        )
        if default_event_product:
            product_id = default_event_product.id
        else:
            product_id = (
                self.env["product.product"]
                .create(
                    {
                        "name": "Generic Registration Product",
                        "list_price": 0,
                        "standard_price": 0,
                        "type": "service",
                    }
                )
                .id
            )
            self.env["ir.model.data"].create(
                {
                    "name": "product_product_event",
                    "module": "event_product",
                    "model": "product.product",
                    "res_id": product_id,
                }
            )
        self.env.cr.execute(
            f"UPDATE {self._table} SET product_id = %s WHERE id = ANY(%s);",
            (product_id, ticket_type_ids),
        )
        return None

    @api.model
    def _get_event_ticket_fields_whitelist(self):
        """Add sale specific fields to copy from template to ticket"""
        return super()._get_event_ticket_fields_whitelist() + ["product_id", "price"]
