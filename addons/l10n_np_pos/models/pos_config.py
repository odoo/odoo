# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    l10n_np_default_customer = fields.Many2one('res.partner', string="Default Customer")
