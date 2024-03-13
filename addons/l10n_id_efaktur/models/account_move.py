# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round, float_repr

FK_HEAD_LIST = ['FK', 'KD_JENIS_TRANSAKSI', 'FG_PENGGANTI', 'NOMOR_FAKTUR', 'MASA_PAJAK', 'TAHUN_PAJAK', 'TANGGAL_FAKTUR', 'NPWP', 'NAMA', 'ALAMAT_LENGKAP', 'JUMLAH_DPP', 'JUMLAH_PPN', 'JUMLAH_PPNBM', 'ID_KETERANGAN_TAMBAHAN', 'FG_UANG_MUKA', 'UANG_MUKA_DPP', 'UANG_MUKA_PPN', 'UANG_MUKA_PPNBM', 'REFERENSI', 'KODE_DOKUMEN_PENDUKUNG']

LT_HEAD_LIST = ['LT', 'NPWP', 'NAMA', 'JALAN', 'BLOK', 'NOMOR', 'RT', 'RW', 'KECAMATAN', 'KELURAHAN', 'KABUPATEN', 'PROPINSI', 'KODE_POS', 'NOMOR_TELEPON']

OF_HEAD_LIST = ['OF', 'KODE_OBJEK', 'NAMA', 'HARGA_SATUAN', 'JUMLAH_BARANG', 'HARGA_TOTAL', 'DISKON', 'DPP', 'PPN', 'TARIF_PPNBM', 'PPNBM']


def _csv_row(data, delimiter=',', quote='"'):
    return quote + (quote + delimiter + quote).join([str(x).replace(quote, '\\' + quote) for x in data]) + quote + '\n'


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_id_tax_number = fields.Char(string="Tax Number", copy=False)
    l10n_id_replace_invoice_id = fields.Many2one('account.move', string="Replace Invoice",  domain="['|', '&', '&', ('state', '=', 'posted'), ('partner_id', '=', partner_id), ('reversal_move_id', '!=', False), ('state', '=', 'cancel')]", copy=False)
    l10n_id_attachment_id = fields.Many2one('ir.attachment', readonly=True, copy=False)
    l10n_id_csv_created = fields.Boolean('CSV Created', compute='_compute_csv_created', copy=False)
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
        ], string='Kode Transaksi', help='Dua digit pertama nomor pajak',
        readonly=False, states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]}, copy=False,
        compute="_compute_kode_transaksi", store=True)
    l10n_id_need_kode_transaksi = fields.Boolean(compute='_compute_need_kode_transaksi')

    @api.onchange('l10n_id_tax_number')
    def _onchange_l10n_id_tax_number(self):
        for record in self:
            if record.l10n_id_tax_number and record.move_type not in self.get_purchase_types():
                raise UserError(_("You can only change the number manually for a Vendor Bills and Credit Notes"))

    @api.depends('l10n_id_attachment_id')
    def _compute_csv_created(self):
        for record in self:
            record.l10n_id_csv_created = bool(record.l10n_id_attachment_id)

    @api.depends('partner_id')
    def _compute_kode_transaksi(self):
        for move in self:
            move.l10n_id_kode_transaksi = move.partner_id.l10n_id_kode_transaksi

    @api.depends('partner_id', 'line_ids.tax_ids')
    def _compute_need_kode_transaksi(self):
        for move in self:
            # If there are no taxes at all on every line (0% taxes counts as having a tax) then we don't need a kode transaksi
            move.l10n_id_need_kode_transaksi = (
                move.partner_id.l10n_id_pkp
                and not move.l10n_id_tax_number
                and move.move_type == 'out_invoice'
                and move.country_code == 'ID'
                and move.line_ids.tax_ids
            )

    @api.constrains('l10n_id_kode_transaksi', 'line_ids', 'partner_id')
    def _constraint_kode_ppn(self):
        ppn_tag = self.env.ref('l10n_id.ppn_tag')
        for move in self.filtered(lambda m: m.l10n_id_need_kode_transaksi and m.l10n_id_kode_transaksi != '08'):
            if any(ppn_tag.id in line.tax_tag_ids.ids for line in move.line_ids if line.display_type == 'product') \
                    and any(ppn_tag.id not in line.tax_tag_ids.ids for line in move.line_ids if line.display_type == 'product'):
                raise UserError(_('Cannot mix VAT subject and Non-VAT subject items in the same invoice with this kode transaksi.'))
        for move in self.filtered(lambda m: m.l10n_id_need_kode_transaksi and m.l10n_id_kode_transaksi == '08'):
            if any(ppn_tag.id in line.tax_tag_ids.ids for line in move.line_ids if line.display_type == 'product'):
                raise UserError('Kode transaksi 08 is only for non VAT subject items.')

    @api.constrains('l10n_id_tax_number')
    def _constrains_l10n_id_tax_number(self):
        for record in self.filtered('l10n_id_tax_number'):
            if record.l10n_id_tax_number != re.sub(r'\D', '', record.l10n_id_tax_number):
                record.l10n_id_tax_number = re.sub(r'\D', '', record.l10n_id_tax_number)
            if len(record.l10n_id_tax_number) != 16:
                raise UserError(_('A tax number should have 16 digits'))
            elif record.l10n_id_tax_number[:2] not in dict(self._fields['l10n_id_kode_transaksi'].selection).keys():
                raise UserError(_('A tax number must begin by a valid Kode Transaksi'))
            elif record.l10n_id_tax_number[2] not in ('0', '1'):
                raise UserError(_('The third digit of a tax number must be 0 or 1'))

    def _post(self, soft=True):
        """Set E-Faktur number after validation."""
        for move in self:
            if move.l10n_id_need_kode_transaksi:
                if not move.l10n_id_kode_transaksi:
                    raise ValidationError(_('You need to put a Kode Transaksi for this partner.'))
                if move.l10n_id_replace_invoice_id.l10n_id_tax_number:
                    if not move.l10n_id_replace_invoice_id.l10n_id_attachment_id:
                        raise ValidationError(_('Replacement invoice only for invoices on which the e-Faktur is generated. '))
                    rep_efaktur_str = move.l10n_id_replace_invoice_id.l10n_id_tax_number
                    move.l10n_id_tax_number = '%s1%s' % (move.l10n_id_kode_transaksi, rep_efaktur_str[3:])
                else:
                    efaktur = self.env['l10n_id_efaktur.efaktur.range'].pop_number(move.company_id.id)
                    if not efaktur:
                        raise ValidationError(_('There is no Efaktur number available.  Please configure the range you get from the government in the e-Faktur menu. '))
                    move.l10n_id_tax_number = '%s0%013d' % (str(move.l10n_id_kode_transaksi), efaktur)
        return super()._post(soft)

    def reset_efaktur(self):
        """Reset E-Faktur, so it can be use for other invoice."""
        for move in self:
            if move.l10n_id_attachment_id:
                raise UserError(_('You have already generated the tax report for this document: %s', move.name))
            self.env['l10n_id_efaktur.efaktur.range'].push_number(move.company_id.id, move.l10n_id_tax_number[3:])
            move.message_post(
                body='e-Faktur Reset: %s ' % (move.l10n_id_tax_number),
                subject="Reset Efaktur")
            move.l10n_id_tax_number = False
        return True

    def download_csv(self):
        action = {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=" + str(self.l10n_id_attachment_id.id) + "&filename_field=name&field=datas&download=true&name=" + self.l10n_id_attachment_id.name,
            'target': 'self'
        }
        return action

    def download_efaktur(self):
        """Collect the data and execute function _generate_efaktur."""
        for record in self:
            if record.state == 'draft':
                raise ValidationError(_('Could not download E-faktur in draft state'))

            if record.partner_id.l10n_id_pkp and not record.l10n_id_tax_number:
                if not self.l10n_id_need_kode_transaksi:
                    raise ValidationError(_('E-faktur is not available for invoices without any taxes.'))
                raise ValidationError(_('Connect %(move_number)s with E-faktur to download this report', move_number=record.name))

        self._generate_efaktur(',')
        return self.download_csv()

    def _generate_efaktur_invoice(self, delimiter):
        """Generate E-Faktur for customer invoice."""
        # Invoice of Customer

        output_head = '%s%s%s' % (
            _csv_row(FK_HEAD_LIST, delimiter),
            _csv_row(LT_HEAD_LIST, delimiter),
            _csv_row(OF_HEAD_LIST, delimiter),
        )

        idr = self.env.ref('base.IDR')

        for move in self.filtered(lambda m: m.state == 'posted'):
            eTax = move._prepare_etax()

            nik = str(move.partner_id.l10n_id_nik) if not move.partner_id.vat else ''

            if move.l10n_id_replace_invoice_id:
                number_ref = str(move.l10n_id_replace_invoice_id.name) + " replaced by " + str(move.name) + " " + nik
            else:
                number_ref = str(move.name) + " " + nik

            street = ', '.join([x for x in (move.partner_id.street, move.partner_id.street2) if x])

            invoice_npwp = '000000000000000'
            if move.partner_id.vat and len(move.partner_id.vat) >= 12:
                invoice_npwp = move.partner_id.vat
            elif (not move.partner_id.vat or len(move.partner_id.vat) < 12) and move.partner_id.l10n_id_nik:
                invoice_npwp = move.partner_id.l10n_id_nik
            invoice_npwp = invoice_npwp.replace('.', '').replace('-', '')

            # Here all fields or columns based on eTax Invoice Third Party
            eTax['KD_JENIS_TRANSAKSI'] = move.l10n_id_tax_number[0:2] or 0
            eTax['FG_PENGGANTI'] = move.l10n_id_tax_number[2:3] or 0
            eTax['NOMOR_FAKTUR'] = move.l10n_id_tax_number[3:] or 0
            eTax['MASA_PAJAK'] = move.invoice_date.month
            eTax['TAHUN_PAJAK'] = move.invoice_date.year
            eTax['TANGGAL_FAKTUR'] = '{0}/{1}/{2}'.format(move.invoice_date.day, move.invoice_date.month, move.invoice_date.year)
            eTax['NPWP'] = invoice_npwp
            eTax['NAMA'] = move.partner_id.name if eTax['NPWP'] == '000000000000000' else move.partner_id.l10n_id_tax_name or move.partner_id.name
            eTax['ALAMAT_LENGKAP'] = move.partner_id.contact_address.replace('\n', '') if eTax['NPWP'] == '000000000000000' else move.partner_id.l10n_id_tax_address or street
            eTax['JUMLAH_DPP'] = int(float_round(move.amount_untaxed, 0, rounding_method="DOWN"))  # currency rounded to the unit
            eTax['JUMLAH_PPN'] = int(float_round(move.amount_tax, 0, rounding_method="DOWN"))  # tax amount ALWAYS rounded down
            eTax['ID_KETERANGAN_TAMBAHAN'] = '1' if move.l10n_id_kode_transaksi == '07' else ''
            eTax['REFERENSI'] = number_ref
            eTax['KODE_DOKUMEN_PENDUKUNG'] = '0'

            lines = move.line_ids.filtered(lambda x: x.move_id._is_downpayment() and x.price_unit < 0 and x.display_type == 'product')
            eTax['FG_UANG_MUKA'] = 0
            eTax['UANG_MUKA_DPP'] = float_repr(abs(sum(lines.mapped(lambda l: float_round(l.price_subtotal, 0)))), 0)
            eTax['UANG_MUKA_PPN'] = float_repr(abs(sum(lines.mapped(lambda l: float_round(l.price_total - l.price_subtotal, 0)))), 0)

            fk_values_list = ['FK'] + [eTax[f] for f in FK_HEAD_LIST[1:]]

            # HOW TO ADD 2 line to 1 line for free product
            free, sales = [], []

            for line in move.line_ids.filtered(lambda l: l.display_type == 'product'):
                # *invoice_line_unit_price is price unit use for harga_satuan's column
                # *invoice_line_quantity is quantity use for jumlah_barang's column
                # *invoice_line_total_price is bruto price use for harga_total's column
                # *invoice_line_discount_m2m is discount price use for diskon's column
                # *line.price_subtotal is subtotal price use for dpp's column
                # *tax_line or free_tax_line is tax price use for ppn's column
                free_tax_line = tax_line = 0.0

                for tax in line.tax_ids:
                    if tax.amount > 0:
                        tax_line += line.price_subtotal * (tax.amount / 100.0)

                discount = 1 - (line.discount / 100)
                # guarantees price to be tax-excluded
                invoice_line_total_price = line.price_subtotal / discount if discount else 0
                invoice_line_unit_price = invoice_line_total_price / line.quantity if line.quantity else 0

                line_dict = {
                    'KODE_OBJEK': line.product_id.default_code or '',
                    'NAMA': line.product_id.name or '',
                    'HARGA_SATUAN': float_repr(idr.round(invoice_line_unit_price), idr.decimal_places),
                    'JUMLAH_BARANG': line.quantity,
                    'HARGA_TOTAL': idr.round(invoice_line_total_price),
                    'DPP': line.price_subtotal,
                    'product_id': line.product_id.id,
                }

                if line.price_subtotal < 0:
                    for tax in line.tax_ids:
                        free_tax_line += (line.price_subtotal * (tax.amount / 100.0)) * -1.0

                    line_dict.update({
                        'DISKON': float_round(invoice_line_total_price - line.price_subtotal, 0),
                        'PPN': free_tax_line,
                    })
                    free.append(line_dict)
                elif line.price_subtotal != 0.0:
                    invoice_line_discount_m2m = invoice_line_total_price - line.price_subtotal

                    line_dict.update({
                        'DISKON': float_round(invoice_line_discount_m2m, 0),
                        'PPN': tax_line,
                    })
                    sales.append(line_dict)

            sub_total_before_adjustment = sub_total_ppn_before_adjustment = 0.0

            # We are finding the product that has affected
            # by free product to adjustment the calculation
            # of discount and subtotal.
            # - the price total of free product will be
            # included as a discount to related of product.
            for sale in sales:
                for f in free:
                    if f['product_id'] == sale['product_id']:
                        sale['DISKON'] = sale['DISKON'] - f['DISKON'] + f['PPN']
                        sale['DPP'] = sale['DPP'] + f['DPP']

                        tax_line = 0

                        for tax in line.tax_ids:
                            if tax.amount > 0:
                                tax_line += sale['DPP'] * (tax.amount / 100.0)

                        sale['PPN'] = tax_line

                        free.remove(f)

                sub_total_before_adjustment += sale['DPP']
                sub_total_ppn_before_adjustment += sale['PPN']

                sale.update({
                    # Use the db currency rounding to float_round the DPP/PPN.
                    # As we will correct them we need them to be close to the final result.
                    'DPP': idr.round(sale['DPP']),
                    'PPN': idr.round(sale['PPN']),
                    'DISKON': float_repr(sale['DISKON'], 0),
                })


            # The total of the base (DPP) and taxes (PPN) must be a integer, equal to the JUMLAH_DPP and JUMLAH_PPN
            # To do so, we adjust the first line in order to achieve the correct total
            if sales:
                diff_dpp = idr.round(eTax['JUMLAH_DPP'] - sum([sale['DPP'] for sale in sales]))
                total_sales_ppn = idr.round(eTax['JUMLAH_PPN'] - sum([sale['PPN'] for sale in sales]))
                # We will add the differences to the first line for which adding the difference will not result in a negative value.
                for sale in sales:
                    if sale['DPP'] + diff_dpp >= 0 and sale['PPN'] + total_sales_ppn >= 0:
                        sale['HARGA_TOTAL'] += diff_dpp
                        sale['DPP'] += diff_dpp
                        diff_dpp = 0
                        sale['PPN'] += total_sales_ppn
                        total_sales_ppn = 0
                        break

                # We couldn't adjust everything in a single line as their values is too low.
                # So we will instead slit the adjustment in multiple lines.
                if diff_dpp or total_sales_ppn:
                    for sale in sales:
                        # DPP
                        sale_dpp = sale['DPP']
                        sale["DPP"] = max(0, sale["DPP"] + diff_dpp)
                        diff_dpp -= (sale["DPP"] - sale_dpp)
                        sale['HARGA_TOTAL'] = sale["DPP"]
                        # PPN
                        sale_ppn = sale['PPN']
                        sale["PPN"] = max(0, sale["PPN"] + total_sales_ppn)
                        total_sales_ppn -= (sale["PPN"] - sale_ppn)

            # Values now being corrected, we can format them for the CSV
            for sale in sales:
                sale.update({
                    'HARGA_TOTAL': float_repr(sale['HARGA_TOTAL'], idr.decimal_places),
                    'DPP': float_repr(sale['DPP'], idr.decimal_places),
                    'PPN': float_repr(sale['PPN'], idr.decimal_places),
                })

            output_head += _csv_row(fk_values_list, delimiter)
            for sale in sales:
                of_values_list = ['OF'] + [str(sale[f]) for f in OF_HEAD_LIST[1:-2]] + ['0', '0']
                output_head += _csv_row(of_values_list, delimiter)

        return output_head

    def _prepare_etax(self):
        # These values are never set
        return {'JUMLAH_PPNBM': 0, 'UANG_MUKA_PPNBM': 0, 'JUMLAH_BARANG': 0, 'TARIF_PPNBM': 0, 'PPNBM': 0}

    def _generate_efaktur(self, delimiter):
        if self.filtered(lambda x: not x.l10n_id_kode_transaksi):
            raise UserError(_('Some documents don\'t have a transaction code'))
        if self.filtered(lambda x: x.move_type != 'out_invoice'):
            raise UserError(_('Some documents are not Customer Invoices'))

        output_head = self._generate_efaktur_invoice(delimiter)
        my_utf8 = output_head.encode("utf-8")
        out = base64.b64encode(my_utf8)

        attachment = self.env['ir.attachment'].create({
            'datas': out,
            'name': 'efaktur_%s.csv' % (fields.Datetime.to_string(fields.Datetime.now()).replace(" ", "_")),
            'type': 'binary',
        })

        for record in self:
            record.message_post(attachment_ids=[attachment.id])
        self.l10n_id_attachment_id = attachment.id
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
