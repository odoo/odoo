from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError

ADDRESS_FIELDS = ('delivery_from_stret', 'delivery_from_zip', 'delivery_from_city', 'delivery_from_state_id', 'delivery_from_country_id')

# Countries that use miles instead of kilometers for distance
_IMPERIAL_COUNTRY_CODES = {'US', 'GB', 'MM', 'LR'}


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
        string="Sender address",
        compute="_compute_delivery_from_address",
        store=True,
    )
    delivery_from_street = fields.Char(string="Street")
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
        string="Max radius",
        default=10.0,
        help="Maximum delivery distance, in the unit shown next to the field.",
    )
    delivery_distance_unit = fields.Selection(
        selection=[('km', 'km'), ('mi', 'mi')],
        string="Distance unit",
        default=lambda self: 'mi' if self.env.company.country_id.code in _IMPERIAL_COUNTRY_CODES else 'km',
    )
    delivery_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Delivery Product",
        default=lambda self: (
            self.env.ref("pos_self_order.product_delivery_template", raise_if_not_found=False)
            or self.env["product.template"]
        ).product_variant_ids[:1],
        help="Product used for delivery fees in self order.",
    )
    delivery_product_price = fields.Float(
        string="Fixed Price",
        default=0.0,
    )
    free_delivery_min_amount = fields.Float(
        string="Free if order amount is above",
        help="Delivery is free when the order total reaches this amount.",
    )
    mail_template_id = fields.Many2one(
        string="Email Confirmation",
        comodel_name='mail.template',
        domain="[('model', '=', 'pos.order')]",
    )

    @api.depends('delivery_from_street', 'delivery_from_city', 'delivery_from_zip', 'delivery_from_state_id', 'delivery_from_country_id')
    def _compute_delivery_from_address(self):
        for preset in self:
            preset.delivery_from_address = f"{preset.delivery_from_street}, {preset.delivery_from_city}, {preset.delivery_from_state_id.name}, {preset.delivery_from_country_id.name}"

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        if not set(ADDRESS_FIELDS).intersection(fields):
            return defaults
        company_configs = self.env['pos.config'].search([('company_id', '=', self.env.company.id)])
        company_preset_ids = (company_configs.mapped('available_preset_ids') | company_configs.mapped('default_preset_id')).ids
        existing = self.search([('id', 'in', company_preset_ids), ('service_at', '=', 'delivery'), ('delivery_from_address', '!=', False)], limit=1)
        if existing:
            for field in (*ADDRESS_FIELDS, 'delivery_from_latitude', 'delivery_from_longitude'):
                if field in fields:
                    defaults[field] = existing[field].id if hasattr(existing[field], 'id') else existing[field]
            return defaults
        company = self.env.company
        if not company.street:
            return defaults
        try:
            result = self.env['base.geocoder'].geo_find(
                self.env['base.geocoder'].geo_query_address(
                    street=company.street,
                    zip=company.zip or '',
                    city=company.city or '',
                    state=company.state_id.name if company.state_id else '',
                    country=company.country_id.name if company.country_id else '',
                ),
                force_country=company.country_id.name if company.country_id else '',
            )
        except UserError:
            return defaults
        if result is None:
            return defaults
        defaults['delivery_from_street'] = company.street
        defaults['delivery_from_city'] = company.city or ''
        defaults['delivery_from_zip'] = company.zip or ''
        defaults['delivery_from_country_id'] = company.country_id.id or False
        defaults['delivery_from_state_id'] = company.state_id.id or False
        defaults['delivery_from_latitude'] = result[0]
        defaults['delivery_from_longitude'] = result[1]
        return defaults

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
            if preset.delivery_from_address and not (preset.delivery_from_latitude or preset.delivery_from_longitude):
                preset._geo_localize_delivery_address()
        return presets

    def _geo_localize_delivery_address(self):
        self.ensure_one()
        if not self.delivery_from_address:
            self.delivery_from_latitude = 0.0
            self.delivery_from_longitude = 0.0
            return
        try:
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
        except UserError:
            return
        if result is not None:
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
        params.extend(['service_at', 'mail_template_id', 'free_delivery_min_amount', 'delivery_product_id', 'delivery_product_price'])
        return params
    
    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params.extend(['mail_template_id'])
        return params

    def _can_return_content(self, field_name=None, access_token=None):
        if field_name in ["image_128", "image_512"]:
            return True
        return super()._can_return_content(field_name, access_token)
