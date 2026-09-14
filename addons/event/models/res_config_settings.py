from odoo import _, api, exceptions, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def _default_use_google_maps_static_api(self):
        api_key = self.env["credential.credential"]._get_system_secret(
            "google_maps.signed_static_api_key"
        )
        api_secret = self.env["credential.credential"]._get_system_secret(
            "google_maps.signed_static_api_secret"
        )
        return bool(api_key and api_secret)

    google_maps_static_api_key = fields.Char(
        string="Google Maps API key",
        compute="_compute_google_maps_static_api_key",
        store=True,
        readonly=False,
        secret_parameter="google_maps.signed_static_api_key",
    )
    google_maps_static_api_secret = fields.Char(
        string="Google Maps API secret",
        compute="_compute_google_maps_static_api_secret",
        store=True,
        readonly=False,
        secret_parameter="google_maps.signed_static_api_secret",
    )
    module_event_sale = fields.Boolean(string="Tickets with Sale")
    module_pos_event = fields.Boolean(string="Tickets with PoS")
    module_website_event_track = fields.Boolean(string="Tracks and Agenda")
    module_website_event_track_live = fields.Boolean(string="Live Mode")
    module_website_event_track_quiz = fields.Boolean(string="Quiz on Tracks")
    module_website_event_exhibitor = fields.Boolean(string="Advanced Sponsors")
    use_event_barcode = fields.Boolean(
        config_parameter="event.use_event_barcode",
        help="Enable or Disable Event Barcode functionality.",
    )
    barcode_nomenclature_id = fields.Many2one(
        comodel_name="barcode.nomenclature",
        related="company_id.nomenclature_id",
        readonly=False,
    )
    module_website_event_sale = fields.Boolean(string="Online Ticketing")
    module_event_booth = fields.Boolean(string="Booth Management")
    use_google_maps_static_api = fields.Boolean(
        string="Google Maps static API",
        default=_default_use_google_maps_static_api,
    )

    @api.depends("use_google_maps_static_api")
    def _compute_google_maps_static_api_key(self):
        """Clear API key on disabling google maps."""
        for config in self:
            if not config.use_google_maps_static_api:
                config.google_maps_static_api_key = ""

    @api.depends("use_google_maps_static_api")
    def _compute_google_maps_static_api_secret(self):
        """Clear API secret on disabling google maps."""
        for config in self:
            if not config.use_google_maps_static_api:
                config.google_maps_static_api_secret = ""

    @api.onchange("module_website_event_track")
    def _onchange_module_website_event_track(self):
        """Reset sub-modules, otherwise you may have track to False but still
        have track_live or track_quiz to True, meaning track will come back due
        to dependencies of modules."""
        for config in self:
            if not config.module_website_event_track:
                config.module_website_event_track_live = False
                config.module_website_event_track_quiz = False

    def _check_google_maps_static_api_secret(self):
        for config in self:
            secret = config.google_maps_static_api_secret
            if (
                secret
                and self.env["res.partner"]._decode_google_maps_secret(secret) is None
            ):
                raise exceptions.UserError(_("Please enter a valid base64 secret"))

    @api.model_create_multi
    def create(self, vals_list):
        configs = super().create(vals_list)
        configs._check_google_maps_static_api_secret()
        return configs

    def write(self, vals):
        result = super().write(vals)
        if vals.get("google_maps_static_api_secret"):
            self._check_google_maps_static_api_secret()
        return result
