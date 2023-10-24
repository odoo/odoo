# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_l10n_us_taxcloud = fields.Boolean(string="L10n US TaxCloud")
