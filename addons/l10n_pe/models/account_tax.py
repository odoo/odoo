# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_pe_edi_tax_code = fields.Selection(
        [
            ('1000', 'IGV - General Sales Tax'),
            ('1016', 'IVAP - Tax on Sale Paddy Rice'),
            ('2000', 'ISC - Selective Excise Tax'),
            ('7152', 'ICBPER - Plastic bag tax'),
            ('9995', 'EXP - Exportation'),
            ('9996', 'GRA - Free'),
            ('9997', 'EXO - Exonerated'),
            ('9998', 'INA - Unaffected'),
            ('9999', 'OTHERS - Other taxes')
        ],
        string='Code',
        help="Peru: SUNAT tax code",
    )

    l10n_pe_edi_unece_category = fields.Selection(
        [
            ('E', 'Exempt from tax'),
            ('G', 'Free export item, tax not charged'),
            ('O', 'Services outside scope of tax'),
            ('S', 'Standard rate'),
            ('Z', 'Zero rated goods')
        ],
        string='UNECE Code',
        help="Peru: Follow the UN/ECE 5305 standard from the United Nations Economic Commission for Europe for more "
             "information http://www.unece.org/trade/untdid/d08a/tred/tred5305.html"
    )
    l10n_pe_edi_isc_type = fields.Selection([
        ('01', 'System to value'),
        ('02', 'Application of the Fixed Amount'),
        ('03', 'Retail Price System'),
    ], 'ISC Type',
        help='Used in Selective Consumption Tax to indicate the type of calculation for the ISC.')
