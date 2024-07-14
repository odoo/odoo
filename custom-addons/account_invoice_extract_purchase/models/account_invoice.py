# -*- coding: utf-8 -*-
import re

from odoo import models, _


class AccountMove(models.Model):
    _inherit = ['account.move']

    def _get_user_infos(self):
        def transform_numbers_to_regex(string):
            r"""Transforms each number of a string to their regex equivalent, i.e. P00042-12 -> P\d{5}-\d{2}"""
            digits_count = 0
            new_string = ''
            for c in string:
                if c.isdigit():
                    digits_count += 1
                else:
                    if digits_count:
                        new_string += r'\d{{{}}}'.format(digits_count) if digits_count > 1 else r'\d'
                    digits_count = 0
                    new_string += c
            if digits_count:
                new_string += r'\d{{{}}}'.format(digits_count) if digits_count > 1 else r'\d'
            return new_string

        user_infos = super(AccountMove, self)._get_user_infos()
        po_sequence = self.env['ir.sequence'].search([('code', '=', 'purchase.order'), ('company_id', 'in', [self.company_id.id, False])], order='company_id', limit=1)
        if po_sequence:
            po_regex_prefix, po_regex_suffix = po_sequence._get_prefix_suffix()
            po_regex_prefix = transform_numbers_to_regex(re.escape(po_regex_prefix))
            po_regex_suffix = transform_numbers_to_regex(re.escape(po_regex_suffix))
            po_regex_sequence = r'\d{{{}}}'.format(po_sequence.padding)
            user_infos['purchase_order_regex'] = po_regex_prefix + po_regex_sequence + po_regex_suffix
        return user_infos

    def _save_form(self, ocr_results, force_write=False):
        if self.move_type == 'in_invoice':
            total_ocr = self._get_ocr_selected_value(ocr_results, 'total', 0.0)

            purchase_orders_ocr = ocr_results['purchase_order']['selected_values'] if 'purchase_order' in ocr_results else []
            purchase_orders_found = [po['content'] for po in purchase_orders_ocr]

            supplier_ocr = self._get_ocr_selected_value(ocr_results, 'supplier', "")
            vat_number_ocr = self._get_ocr_selected_value(ocr_results, 'VAT_Number', "")
            partner_id = self._find_partner_id_with_vat(vat_number_ocr).id or self._find_partner_id_with_name(supplier_ocr)

            self._find_and_set_purchase_orders(purchase_orders_found, partner_id, total_ocr, from_ocr=True)

        return super()._save_form(ocr_results, force_write=force_write)
