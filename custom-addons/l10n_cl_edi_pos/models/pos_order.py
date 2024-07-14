# -*- coding: utf-8 -*-
from odoo import models, fields


class PosOrder(models.Model):
    _inherit = 'pos.order'

    invoice_type = fields.Char(string="Invoice Type")
    voucher_number = fields.Char(string="Voucher Number")

    def _export_for_ui(self, order):
        fields = super()._export_for_ui(order)
        if self.env.company.country_code == 'CL':
            fields['voucher_number'] = order.voucher_number
            fields['l10n_latam_document_type'] = order.account_move.l10n_latam_document_type_id.name if order.account_move else False
            fields['l10n_latam_document_number'] = order.account_move.l10n_latam_document_number if order.account_move else False
            fields['l10n_cl_sii_regional_office'] = dict(self.env.company._fields['l10n_cl_sii_regional_office'].selection).get(self.env.company.l10n_cl_sii_regional_office)
            fields['l10n_cl_sii_barcode'] = order.account_move._pdf417_barcode(order.account_move.l10n_cl_sii_barcode) if order.account_move.l10n_cl_sii_barcode else False
        return fields

    def _order_fields(self, ui_order):
        fields = super()._order_fields(ui_order)
        if self.env.company.country_code == 'CL':
            fields['invoice_type'] = ui_order['invoiceType'] if 'invoiceType' in ui_order else "boleta"
            fields['voucher_number'] = ui_order['voucherNumber'] if 'voucherNumber' in ui_order else False
        return fields

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        if self.amount_total >= 0:
            if self.invoice_type == 'factura':
                if self.amount_tax == 0:
                    vals.update({
                        'l10n_latam_document_type_id': self.env.ref('l10n_cl.dc_y_f_dte').id,
                    })
                else:
                    vals.update({
                        'l10n_latam_document_type_id': self.env.ref('l10n_cl.dc_a_f_dte').id,
                    })
            elif self.invoice_type == 'boleta':
                if self.amount_tax == 0:
                    vals.update({
                        'l10n_latam_document_type_id': self.env.ref('l10n_cl.dc_b_e_dte').id,
                    })
                else:
                    vals.update({
                        'l10n_latam_document_type_id': self.env.ref('l10n_cl.dc_b_f_dte').id,
                    })
        else:
            #Document type for refunds
            vals.update({
                'l10n_latam_document_type_id': self.env.ref('l10n_cl.dc_nc_f_dte').id,
            })

        return vals

    def _create_invoice(self, move_vals):
        move = super()._create_invoice(move_vals)
        if self.env.company.country_code == 'CL':
            if move.reversed_entry_id:
                reversed_move_id = self.env['account.move'].browse(move.reversed_entry_id.id)
                refunded_order_id = self.env['pos.order'].search([('account_move', '=', move.reversed_entry_id.id)], limit=1)
                refunded_order_order_lines_ids = self.env['pos.order.line'].search([('order_id', '=', refunded_order_id.id)])
                refunded_order_order_lines_set = set()
                for order_line in refunded_order_order_lines_ids:
                    refunded_order_order_lines_set.add((order_line.id, order_line.qty))
                refunded_order_lines_set = set()
                order_lines_ids = self.env['pos.order.line'].search([('order_id', '=', self.id)])
                for order_line in order_lines_ids:
                    refunded_order_lines_set.add((order_line.refunded_orderline_id.id, -order_line.qty))
                reference_doc_code = '3'
                if refunded_order_order_lines_set == refunded_order_lines_set:
                    reference_doc_code = '1'

                self.env['l10n_cl.account.invoice.reference'].create({
                    'move_id': move.id,
                    'origin_doc_number': reversed_move_id.l10n_latam_document_number,
                    'l10n_cl_reference_doc_type_id': reversed_move_id.l10n_latam_document_type_id.id,
                    'reference_doc_code': reference_doc_code,
                    'reason': 'Anulación NC por aceptación con reparo (' + reversed_move_id.l10n_latam_document_number + ')',
                    'date': move.date,
                })
        return move

    def get_cl_pos_info(self):
        result = []
        for order in self:
            result.append({
                'l10n_latam_document_type': order.account_move.l10n_latam_document_type_id.name,
                'l10n_latam_document_number': order.account_move.l10n_latam_document_number,
                'l10n_cl_sii_regional_office': dict(self.env.company._fields['l10n_cl_sii_regional_office'].selection).get(self.env.company.l10n_cl_sii_regional_office),
                'l10n_cl_sii_barcode': order.account_move._pdf417_barcode(order.account_move.l10n_cl_sii_barcode) if order.account_move.l10n_cl_sii_barcode else False,
            })
        return result
