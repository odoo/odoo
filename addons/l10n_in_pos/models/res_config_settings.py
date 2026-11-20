# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_l10n_in_b2c_invoice_prefix = fields.Char(related='pos_config_id.l10n_in_b2c_invoice_prefix', readonly=False)
