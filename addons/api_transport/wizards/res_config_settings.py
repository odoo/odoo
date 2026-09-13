from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    api_transport_log_retention_days = fields.Integer(
        string="Request Log Retention (days)",
        default=90,
        config_parameter="api_transport.log_retention_days",
        help="How long to keep request logs before automatic deletion",
    )
    api_transport_max_cache_entries = fields.Integer(
        string="API Max Cache Entries",
        default=10000,
        config_parameter="api_transport.max_cache_entries",
        help="Maximum number of cached API responses to keep",
    )
