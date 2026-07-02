# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_vn_symbol_id = fields.Many2one(
        comodel_name='l10n_vn.sinvoice.symbol',
        string='Default Invoice Symbol',
        help='If set, this symbol will be used as the default symbol for all invoices of this company.',
        domain=[('usage', '=', 'invoice')],
    )
