# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class Partner(models.Model):
    _inherit = "res.partner"

    l10n_id_tku = fields.Char(
        default="000000",
        string="TKU",
        help="Branch Number of your company, 000000 is the default for headquarters"
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
        selection=[
            ('01', '01 To the Parties that is not VAT Collector (Regular Customers)'),
            ('02', '02 To the Treasurer'),
            ('03', '03 To other VAT Collectors other than the Treasurer'),
            ('04', '04 Other Value of VAT Imposition Base'),
            ('05', '05 Specified Amount (Article 9A Paragraph (1) VAT Law)'),
            ('06', '06 to individuals holding foreign passports'),
            ('07', '07 Deliveries that the VAT is not Collected'),
            ('08', '08 Deliveries that the VAT is Exempted'),
            ('09', '09 Deliveries of Assets (Article 16D of VAT Law)'),
            ('10', '10 Other deliveries'),
        ],
        string='Invoice Transaction Code',
        help='Dua digit pertama nomor pajak',
        default='01',
        tracking=True,
    )

    @api.depends('vat', 'country_code')
    def _compute_l10n_id_pkp(self):
        for record in self:
            record.l10n_id_pkp = record.vat and record.country_code == 'ID'
