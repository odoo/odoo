from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..tools import debug_log as dbg


class PosCategory(models.Model):
    _name = "pos.category"
    _description = "Point of Sale Category"
    _inherit = ["mixin.pos.load", "mixin.color"]
    _order = "sequence, name"

    @api.constrains("parent_id")
    def _check_category_recursion(self):
        if self._has_cycle():
            raise ValidationError(_("Error! You cannot create recursive categories."))

    _color_default_indices = tuple(range(11))

    display_name = fields.Char(recursive=True)

    name = fields.Char(
        string="Category Name",
        translate=True,
        required=True,
    )
    parent_id = fields.Many2one(
        comodel_name="pos.category",
        string="Parent Category",
        index=True,
    )
    child_ids = fields.One2many(
        comodel_name="pos.category",
        inverse_name="parent_id",
        string="Children Categories",
    )
    sequence = fields.Integer(
        help="Gives the sequence order when displaying a list of product categories."
    )
    image_512 = fields.Image(
        string="Image",
        max_width=512,
        max_height=512,
    )
    image_128 = fields.Image(
        related="image_512",
        string="Image 128",
        max_width=128,
        max_height=128,
        store=True,
    )
    color = fields.Integer(
        default=lambda self: self._default_color(),
        required=False,
    )
    hour_until = fields.Float(
        string="Availability Until",
        default=24.0,
        help="The product will be available until this hour for online order and self order.",
    )
    hour_after = fields.Float(
        string="Availability After",
        default=0.0,
        help="The product will be available after this hour for online order and self order.",
    )

    has_image = fields.Boolean(compute="_compute_has_image")

    @api.model
    def _load_pos_data_domain(self, data, config):
        domain = []
        if config.limit_categories:
            preparation_categories = [
                printer["product_categories_ids"] for printer in data["pos.printer"]
            ]
            flattened_preparation_categories = [
                item for sublist in preparation_categories for item in sublist
            ]
            domain += [
                (
                    "id",
                    "in",
                    flattened_preparation_categories
                    + config.iface_available_categ_ids.ids,
                )
            ]
            dbg.logic.debug(
                "[load:pos.category] limited: %d printer + %d config categories",
                len(flattened_preparation_categories),
                len(config.iface_available_categ_ids),
            )
        return domain

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            "id",
            "name",
            "parent_id",
            "child_ids",
            "write_date",
            "has_image",
            "color",
            "sequence",
            "hour_until",
            "hour_after",
        ]

    @api.depends("name", "parent_id.display_name")
    @api.depends_context("lang")
    def _compute_display_name(self):
        super()._compute_display_name()
        for cat in self:
            cat.display_name = " / ".join(
                [cat.parent_id.display_name, cat.name or ""]
                if cat.parent_id
                else [cat.name or ""]
            )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_session_open(self):
        blocking_session = (
            self.env["pos.session"]
            .sudo()
            .search(
                [
                    ("state", "!=", "closed"),
                    ("company_id", "in", self.env.companies.ids),
                    "|",
                    "|",
                    ("config_id.limit_categories", "=", False),
                    ("config_id.iface_available_categ_ids", "in", self.ids),
                    ("config_id.printer_ids.product_categories_ids", "in", self.ids),
                ],
                limit=1,
            )
        )
        if blocking_session:
            dbg.logic.debug(
                "pos.category unlink of %s refused by open %s",
                dbg.rec(self),
                dbg.rec(blocking_session),
            )
            raise UserError(
                _(
                    "You cannot delete a point of sale category while the session"
                    " %(session)s of %(config)s is still opened.",
                    session=blocking_session.name,
                    config=blocking_session.config_id.name,
                )
            )

    @api.depends("image_128")
    def _compute_has_image(self):
        for category in self:
            category.has_image = bool(category.image_128)

    @api.constrains("hour_until", "hour_after")
    def _check_hour(self):
        for category in self:
            if not 0.0 <= category.hour_until <= 24.0:
                raise ValidationError(
                    _("The Availability Until must be set between 00:00 and 24:00")
                )
            if not 0.0 <= category.hour_after <= 24.0:
                raise ValidationError(
                    _("The Availability After must be set between 00:00 and 24:00")
                )
            if category.hour_until < category.hour_after:
                raise ValidationError(
                    _("The Availability Until must be greater than Availability After.")
                )
