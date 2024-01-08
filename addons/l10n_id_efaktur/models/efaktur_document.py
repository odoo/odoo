# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools import float_repr, float_round

FK_HEAD_LIST = ['FK', 'KD_JENIS_TRANSAKSI', 'FG_PENGGANTI', 'NOMOR_FAKTUR', 'MASA_PAJAK', 'TAHUN_PAJAK', 'TANGGAL_FAKTUR', 'NPWP', 'NAMA', 'ALAMAT_LENGKAP', 'JUMLAH_DPP', 'JUMLAH_PPN', 'JUMLAH_PPNBM', 'ID_KETERANGAN_TAMBAHAN', 'FG_UANG_MUKA', 'UANG_MUKA_DPP', 'UANG_MUKA_PPN', 'UANG_MUKA_PPNBM', 'REFERENSI', 'KODE_DOKUMEN_PENDUKUNG']

LT_HEAD_LIST = ['LT', 'NPWP', 'NAMA', 'JALAN', 'BLOK', 'NOMOR', 'RT', 'RW', 'KECAMATAN', 'KELURAHAN', 'KABUPATEN', 'PROPINSI', 'KODE_POS', 'NOMOR_TELEPON']

OF_HEAD_LIST = ['OF', 'KODE_OBJEK', 'NAMA', 'HARGA_SATUAN', 'JUMLAH_BARANG', 'HARGA_TOTAL', 'DISKON', 'DPP', 'PPN', 'TARIF_PPNBM', 'PPNBM']


def _csv_row(data, delimiter=',', quote='"'):
    return quote + (quote + delimiter + quote).join([str(x).replace(quote, '\\' + quote) for x in data]) + quote + '\n'


class EfakturDocument(models.Model):
    _name = "l10n_id_efaktur.document"
    _description = "E-faktur Document"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        compute='_compute_name',
        store=True,
        readonly=False,
        required=True,
        precompute=True,
    )
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
    active = fields.Boolean(
        string="Active",
        default=True,
    )
    invoice_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="l10n_id_efaktur_document",
        domain="[('move_type', 'in', ['out_invoice', 'out_refund']), ('company_id', '=', company_id), ('l10n_id_efaktur_document', '=', False), ('l10n_id_tax_number', '!=', False), ('state', '=', 'posted')]",
        tracking=True,
    )
    attachment_id = fields.Many2one(comodel_name="ir.attachment", readonly=True)

    def action_download(self):
        """ Download the e-faktur related attachment """
        for document in self:
            if not document.attachment_id:
                document._generate_csv()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/l10n_id_efaktur/download_attachments/{",".join(map(str, self.attachment_id.ids))}',
        }

    def action_regenerate(self):
        """ Regenerate the e-faktur csv file, based on the invoice in the document.
        All new file generation will log a copy of the attachment to keep track of past generations.
        """
        self._generate_csv()

    def _generate_csv(self, delimiter=','):
        self.ensure_one()
        if self.invoice_ids.filtered(lambda x: not x.l10n_id_kode_transaksi):
            raise UserError(_("Some documents don't have a transaction code"))
        if self.invoice_ids.filtered(lambda x: x.move_type != 'out_invoice'):
            raise UserError(_("Some documents are not Customer Invoices"))

        output_head = self._generate_efaktur_invoice(delimiter)
        raw_data = output_head.encode("utf-8")

        # create/update attachment and link it to efaktur document if new
        if not self.attachment_id:
            attachment = self.env['ir.attachment'].create({
                'raw': raw_data,
                'name': 'efaktur_%s.csv' % (fields.Datetime.to_string(fields.Datetime.now()).replace(" ", "_")),
                'type': 'binary',
                'res_model': 'l10n_id_efaktur.document',
                'res_id': self.id,
            })
            self.attachment_id = attachment.id
        else:
            attachment = self.attachment_id
            self.attachment_id.write({
                'raw': raw_data,
                'name': 'efaktur_%s.csv' % (fields.Datetime.to_string(fields.Datetime.now()).replace(" ", "_")),
            })

        self.message_post(
            body=_("The e-Faktur report has been generated"),
            attachments=[(attachment.name, attachment.raw)]
        )

    def _generate_efaktur_invoice(self, delimiter=','):
        """Generate E-Faktur for customer invoice."""
        # Invoice of Customer

        output_head = '%s%s%s' % (
            _csv_row(FK_HEAD_LIST, delimiter),
            _csv_row(LT_HEAD_LIST, delimiter),
            _csv_row(OF_HEAD_LIST, delimiter),
        )

        idr = self.env.ref('base.IDR')

        for move in self.invoice_ids.filtered(lambda m: m.state == 'posted'):
            eTax = move._prepare_etax()

            commercial_partner = move.partner_id.commercial_partner_id
            nik = str(commercial_partner.l10n_id_nik) if not commercial_partner.vat else ''

            if move.l10n_id_replace_invoice_id:
                number_ref = str(move.l10n_id_replace_invoice_id.name) + " replaced by " + str(move.name) + " " + nik
            elif nik:
                number_ref = str(move.name) + " " + nik
            else:
                number_ref = str(move.name)

            invoice_npwp = ''
            if commercial_partner.vat and len(commercial_partner.vat) >= 15:
                invoice_npwp = commercial_partner.vat
            elif commercial_partner.l10n_id_nik:
                invoice_npwp = commercial_partner.l10n_id_nik
            if not invoice_npwp:
                action_error = {
                    'view_mode': 'form',
                    'res_model': 'res.partner',
                    'type': 'ir.actions.act_window',
                    'res_id': commercial_partner.id,
                    'views': [[self.env.ref('base.view_partner_form').id, 'form']],
                }
                msg = _("Please make sure that you've input the appropriate NPWP or NIK for the following customer")
                raise RedirectWarning(msg, action_error, _("Edit Customer Information"))
            invoice_npwp = invoice_npwp.replace('.', '').replace('-', '')

            etax_name = commercial_partner.name
            if invoice_npwp[:15] == '000000000000000' and commercial_partner.l10n_id_nik:
                etax_name = "%s#NIK#NAMA#%s" % (commercial_partner.l10n_id_nik, etax_name)

            # Here all fields or columns based on eTax Invoice Third Party
            eTax['KD_JENIS_TRANSAKSI'] = move.l10n_id_tax_number[0:2] or 0
            eTax['FG_PENGGANTI'] = move.l10n_id_tax_number[2:3] or 0
            eTax['NOMOR_FAKTUR'] = move.l10n_id_tax_number[3:] or 0
            eTax['MASA_PAJAK'] = move.invoice_date.month
            eTax['TAHUN_PAJAK'] = move.invoice_date.year
            eTax['TANGGAL_FAKTUR'] = move.invoice_date.strftime("%-d/%-m/%Y")
            eTax['NPWP'] = invoice_npwp
            eTax['NAMA'] = etax_name
            eTax['ALAMAT_LENGKAP'] = move.partner_id.contact_address.replace('\n', '').strip()
            eTax['JUMLAH_DPP'] = int(float_round(move.amount_untaxed, 0))  # currency rounded to the unit
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
                diff_dpp = idr.round(eTax['JUMLAH_DPP'] - sum(sale['DPP'] for sale in sales))
                total_sales_ppn = idr.round(eTax['JUMLAH_PPN'] - sum(sale['PPN'] for sale in sales))
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

    @api.depends('invoice_ids')
    def _compute_name(self):
        """ First compute will be done at creation, from a selection of invoice(s).
        We still want to allow to rename the document to another name if it makes sense.
        """
        for doc in self:
            sorted_invoices = doc.invoice_ids.sorted('name')
            name = []
            if sorted_invoices:
                name.append(sorted_invoices[0].name)
                if len(sorted_invoices) > 1:
                    name.append(sorted_invoices[-1].name)
            doc.name = "%s - Efaktur (%s)" % (fields.Date.context_today(doc).strftime("%Y%m%d"), "....".join(name))
