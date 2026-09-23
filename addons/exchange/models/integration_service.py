from odoo import fields, models


class IntegrationService(models.Model):
    _inherit = "integration.service"

    exchange_channel_ids = fields.One2many(
        comodel_name="exchange.channel",
        inverse_name="endpoint_id",
    )
