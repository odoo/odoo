# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    l10n_ar_country_code = fields.Char(related='company_id.country_id.code', string='Country Code')
