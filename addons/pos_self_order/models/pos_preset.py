from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

ADDRESS_FIELDS = ('delivery_from_address', 'delivery_from_zip', 'delivery_from_city', 'delivery_from_state_id', 'delivery_from_country_id')


class PosPreset(models.Model):
    _inherit = "pos.preset"

    available_in_self = fields.Boolean(string='Available in self', default=False)
    service_at = fields.Selection(
        [("counter", "Pickup zone"), ("table", "Table"), ("delivery", "Delivery")],
        string="Service at",
        default="counter",
        required=True,
    )
    delivery_from_address = fields.Char(
        string="Delivery From",
    )
    delivery_from_city = fields.Char(string="City")
    delivery_from_zip = fields.Char(string="Zip")
    delivery_from_country_id = fields.Many2one(
        comodel_name="res.country",
        string="Country",
    )
    delivery_from_state_id = fields.Many2one(
        comodel_name="res.country.state",
        string="State",
    )
    delivery_from_latitude = fields.Float(string="Latitude", digits=(10, 7))
    delivery_from_longitude = fields.Float(string="Longitude", digits=(10, 7))
    delivery_max_distance_km = fields.Float(
        string="Max Delivery Distance (km)",
        default=10.0,
        help="Maximum delivery distance in kilometers.",
    )
    delivery_product_id = fields.Many2one(
        comodel_name="product.template",
        string="Delivery Product",
        default=lambda self: self.env.ref(
            "pos_self_order.product_delivery_template", raise_if_not_found=False
        ),
        help="Product used for delivery fees in self order.",
    )
    delivery_product_price = fields.Float(
        string="Delivery Price",
        related="delivery_product_id.list_price",
        readonly=False,
    )
    free_delivery_min_amount = fields.Float(
        string="Free Delivery From",
        help="Delivery is free when the order total reaches this amount.",
    )
    mail_template_id = fields.Many2one(
        string="Email Confirmation",
        comodel_name='mail.template',
        domain="[('model', '=', 'pos.order')]",
    )

    def write(self, vals):
        res = super().write(vals)
        if any(field in vals for field in ADDRESS_FIELDS):
            for preset in self:
                preset._geo_localize_delivery_address()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        presets = super().create(vals_list)
        for preset in presets:
            if preset.delivery_from_address:
                preset._geo_localize_delivery_address()
        return presets

    def _geo_localize_delivery_address(self):
        self.ensure_one()
        if not self.delivery_from_address:
            self.delivery_from_latitude = 0.0
            self.delivery_from_longitude = 0.0
            return
        result = self.env['base.geocoder'].geo_find(
            self.env['base.geocoder'].geo_query_address(
                street=self.delivery_from_address,
                zip=self.delivery_from_zip,
                city=self.delivery_from_city,
                state=(self.delivery_from_state_id.name if self.delivery_from_state_id else ""),
                country=(self.delivery_from_country_id.name if self.delivery_from_country_id else ""),
            ),
            force_country=self.delivery_from_country_id.name if self.delivery_from_country_id else ""
        )
        if result and result[0] and result[1]:
            self.delivery_from_latitude = result[0]
            self.delivery_from_longitude = result[1]
        else:
            raise ValidationError(_("The delivery address could not be geolocated. Please enter a valid address."))

    # will be overridden.
    @api.model
    def _load_pos_self_data_domain(self, data, config):
        return ['|', ('id', '=', config.default_preset_id.id), '&', ('available_in_self', '=', True), ('id', 'in', config.available_preset_ids.ids)]

    @api.model
    def _load_pos_self_data_fields(self, config):
        params = super()._load_pos_self_data_fields(config)
        params.extend(['service_at', 'mail_template_id', 'free_delivery_min_amount'])
        return params

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params.extend(['mail_template_id', 'free_delivery_min_amount'])
        return params

    def _can_return_content(self, field_name=None, access_token=None):
        if field_name in ["image_128", "image_512"]:
            return True
        return super()._can_return_content(field_name, access_token)
