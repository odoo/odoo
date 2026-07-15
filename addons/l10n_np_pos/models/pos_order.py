# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_np_default_customer = fields.Many2one(related='config_id.l10n_np_default_customer')
