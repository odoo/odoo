from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EventBoothConfigurator(models.TransientModel):
    _name = "event.booth.configurator"
    _description = "Event Booth Configurator"

    product_id = fields.Many2one(
        comodel_name="product.product",
        readonly=True,
    )
    sale_order_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        readonly=True,
    )
    event_id = fields.Many2one(
        comodel_name="event.event",
        required=True,
    )
    event_booth_category_available_ids = fields.Many2many(
        related="event_id.event_booth_category_available_ids",
        readonly=True,
    )
    event_booth_category_id = fields.Many2one(
        comodel_name="event.booth.category",
        string="Booth Category",
        compute="_compute_event_booth_category_id",
        store=True,
        readonly=False,
        required=True,
    )
    event_booth_ids = fields.Many2many(
        comodel_name="event.booth",
        string="Booth",
        compute="_compute_event_booth_ids",
        store=True,
        readonly=False,
        required=True,
    )

    @api.depends("event_id")
    def _compute_event_booth_category_id(self):
        self.event_booth_category_id = False

    @api.depends("event_id", "event_booth_category_id")
    def _compute_event_booth_ids(self):
        self.event_booth_ids = False

    @api.constrains("event_booth_ids")
    def _check_if_no_booth_ids(self):
        if any(not wizard.event_booth_ids for wizard in self):
            raise ValidationError(_("You have to select at least one booth."))
