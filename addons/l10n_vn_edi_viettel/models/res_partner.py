# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('vn_sinvoice', 'Vietnam (SInvoice)')])
    l10n_vn_edi_symbol = fields.Many2one(
        comodel_name='l10n_vn_edi_viettel.sinvoice.symbol',
        string='Default Symbol',
        help='If set, this symbol will be used as the default symbol for all invoices of this customer.',
        company_dependent=True,
        copy=False,
    )
