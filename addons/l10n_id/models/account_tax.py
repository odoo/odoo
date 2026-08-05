# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_id_ebupot_facility = fields.Selection(selection=[
        ('N/A', 'N/A - Tanpa Fasilitas'),
        ('TaxExAr22', 'TaxExAr22 - Surat Keterangan Bebas (SKB) Pemotongan PPh Pasal 22'),
        ('TaxExAr23', 'TaxExAr23 - Surat Keterangan Bebas (SKB) Pemotongan PPh Pasal 23'),
        ('TaxExIntDep', 'TaxExIntDep - Surat Keterangan Bebas (SKB) Pemotongan PPh atas Bunga atas Deposito Berjangka dan tabungan'),
        ('TaxExIntPhtb', 'TaxExIntPhtb - Surat Keterangan Bebas (SKB) Pemotongan PPh atas Pengalihan Hak atas Tanah dan Bangunan'),
        ('DTP', 'DTP - PPh Ditanggung Pemerintah (DTP)'),
        ('PP23', 'PP23 - Surat Keterangan  PP 23/2018'),
        ('ETC', 'ETC - Fasilitas Lainnya')],
        string="Facility Code",
        help="Used when your transaction partner is entitled to a tax withholding exemption, or a reduced withholding tax rate.",
    )
    l10n_id_ebupot_code = fields.Many2one(
        comodel_name='l10n_id.ebupot.code',
        string="Object Code",
        help="The type of income and the withheld tax rate (such as PPH22, PPH23, PPH Pasal 4 Ayat 2).",
    )
