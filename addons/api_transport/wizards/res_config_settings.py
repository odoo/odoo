from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    api_transport_log_retention_days = fields.Integer(
        string="Request Log Retention (days)",
        help="How long to keep request logs before automatic deletion",
        default=90,
        config_parameter="api_transport.log_retention_days",
    )
    api_transport_max_cache_entries = fields.Integer(
        string="API Max Cache Entries",
        help="Maximum number of cached API responses to keep",
        default=10000,
        config_parameter="api_transport.max_cache_entries",
    )
