# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import product


class ResConfigSettings(product.ResConfigSettings):

    google_custom_search_key = fields.Char(
        string="Google Custom Search API Key",
        config_parameter='google.custom_search.key',
    )
    google_pse_id = fields.Char(
        string="The identifier of the Google Programmable Search Engine",
        config_parameter='google.pse.id',
    )
