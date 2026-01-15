# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.l10n_id_efaktur_coretax.models.account_move import TAX_TRANSACTION_CODE

class Partner(models.Model):
    _inherit = "res.partner"

    l10n_id_tku = fields.Char(
        string="TKU",
        help="Branch Number of your company, leave empty for headquarters"
    )

    # document selection
    l10n_id_buyer_document_type = fields.Selection([
        ('TIN', 'TIN'),
        ('NIK', 'NIK'),
        ('Passport', 'Passport'),
        ('Other', 'Others')
    ], default='TIN', string="Document Type")
    l10n_id_buyer_document_number = fields.Char(string="Document Number")
    l10n_id_nik = fields.Char(string='NIK')
    l10n_id_pkp = fields.Boolean(string="Is PKP", compute='_compute_l10n_id_pkp', store=True, readonly=False, help="Denoting whether the following partner is taxable")
    l10n_id_kode_transaksi = fields.Selection(
        selection=TAX_TRANSACTION_CODE,
        string='Invoice Transaction Code',
        help="he first 2 digits of tax code",
        default='04',
        tracking=True,
    )

    @api.depends('vat', 'country_code')
    def _compute_l10n_id_pkp(self):
        for partner in self:
            partner.l10n_id_pkp = partner.vat and partner.country_code == 'ID'
