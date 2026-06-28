# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_vn_pos_default_symbol = fields.Many2one(
        comodel_name='l10n_vn_edi_viettel.sinvoice.symbol',
        string='Default PoS Symbol',
    )
