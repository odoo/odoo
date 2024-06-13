# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    google_custom_search_key = fields.Char(
        string="Google Custom Search API Key",
        config_parameter='google.custom_search.key',
    )
    google_pse_id = fields.Char(
        string="The identifier of the Google Programmable Search Engine",
        config_parameter='google.pse.id',
    )
