from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    calendar_external_videocall_link_generation = fields.Boolean("Generate meeting link automatically",
        config_parameter="calendar.calendar_external_videocall_link_generation")
