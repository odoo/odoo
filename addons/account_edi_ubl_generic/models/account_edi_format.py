# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

import base64


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    ####################################################
    # Import
    ####################################################

    def _is_ubl(self, filename, tree):
        return self.code == 'ubl_2_1' and super()._is_generic_ubl(filename, tree)

    ####################################################
    # Export
    ####################################################

    def _get_ubl_values(self, invoice):
        values = super()._get_ubl_values(invoice)
        if self.code != 'ubl_2_1':
            return values

        values['ubl_version'] = '2.1'
        return values

    def _export_ubl(self, invoice):
        self.ensure_one()
        # Create file content.
        xml_content = b"<?xml version='1.0' encoding='UTF-8'?>"
        xml_content += self.env.ref('account_edi_ubl.export_ubl_invoice')._render(self._get_ubl_values(invoice))
        xml_name = '%s_ubl_2_1.xml' % (invoice.name.replace('/', '_'))
        return self.env['ir.attachment'].create({
            'name': xml_name,
            'datas': base64.encodebytes(xml_content),
            'res_model': 'account.move',
            'res_id': invoice._origin.id,
            'mimetype': 'application/xml'
        })

    ####################################################
    # Account.edi.format override
    ####################################################

    def _is_compatible_with_journal(self, journal):
        self.ensure_one()
        res = super()._is_compatible_with_journal(journal)
        if self.code != 'ubl_2_1':
            return res
        return journal.type == 'sale'

    def _post_invoice_edi(self, invoices, test_mode=False):
        self.ensure_one()
        if self.code != 'ubl_2_1':
            return super()._post_invoice_edi(invoices, test_mode=test_mode)
        res = {}
        for invoice in invoices:
            attachment = self._export_ubl(invoice)
            res[invoice] = {'attachment': attachment}
        return res

    def _is_embedding_to_invoice_pdf_needed(self):
        self.ensure_one()
        if self.code != 'ubl_2_1':
            return super()._is_embedding_to_invoice_pdf_needed()
        return False  # ubl must not be embedded to PDF.

    def _create_invoice_from_xml_tree(self, filename, tree):
        self.ensure_one()
        if self._is_ubl(filename, tree):
            return self._import_ubl(tree, self.env['account.move'])
        return super()._create_invoice_from_xml_tree(filename, tree)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        self.ensure_one()
        if self._is_ubl(filename, tree):
            return self._import_ubl(tree, invoice)
        return super()._update_invoice_from_xml_tree(filename, tree, invoice)
