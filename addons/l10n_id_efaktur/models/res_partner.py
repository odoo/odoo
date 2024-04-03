# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResPartner(models.Model):
    """Inherit res.partner object to add NPWP field and Kode Transaksi"""
    _inherit = "res.partner"

    l10n_id_pkp = fields.Boolean(string="ID PKP", compute='_compute_l10n_id_pkp', store=True, readonly=False)
    l10n_id_nik = fields.Char(string='NIK')
    l10n_id_tax_address = fields.Char('Tax Address')
    l10n_id_tax_name = fields.Char('Tax Name')
    l10n_id_kode_transaksi = fields.Selection([
            ('01', '01 Kepada Pihak yang Bukan Pemungut PPN (Customer Biasa)'),
            ('02', '02 Kepada Pemungut Bendaharawan (Dinas Kepemerintahan)'),
            ('03', '03 Kepada Pemungut Selain Bendaharawan (BUMN)'),
            ('04', '04 DPP Nilai Lain (PPN 1%)'),
            ('05', '05 Besaran Tertentu'),
            ('06', '06 Penyerahan Lainnya (Turis Asing)'),
            ('07', '07 Penyerahan yang PPN-nya Tidak Dipungut (Kawasan Ekonomi Khusus/ Batam)'),
            ('08', '08 Penyerahan yang PPN-nya Dibebaskan (Impor Barang Tertentu)'),
            ('09', '09 Penyerahan Aktiva ( Pasal 16D UU PPN )'),
        ],
        string='Kode Transaksi',
        help='Dua digit pertama nomor pajak',
        default='01',
    )

    @api.depends('vat', 'country_code')
    def _compute_l10n_id_pkp(self):
        for record in self:
            record.l10n_id_pkp = record.vat and record.country_code == 'ID'


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_id_tax_address = fields.Char('Tax Address', related='company_id.partner_id.l10n_id_tax_address', readonly=False)
    l10n_id_tax_name = fields.Char('Tax Name', related='company_id.partner_id.l10n_id_tax_address', readonly=False)
