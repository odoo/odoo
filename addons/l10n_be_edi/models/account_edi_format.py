# -*- coding: utf-8 -*-

from odoo import models

import base64
import markupsafe


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    ####################################################
    # Export
    ####################################################

    def _get_efff_values(self, invoice):
        return {
            **self._get_ubl_values(invoice),
            'ubl_version': 2.0,
        }

    def _export_efff(self, invoice):
        self.ensure_one()
        # Create file content.
        xml_content = markupsafe.Markup("<?xml version='1.0' encoding='UTF-8'?>")
        xml_content += self.env.ref('l10n_be_edi.export_efff_invoice')._render(self._get_efff_values(invoice))
        xml_name = '%s.xml' % invoice._get_efff_name()
        return self.env['ir.attachment'].create({
            'name': xml_name,
            'raw': xml_content.encode(),
            'mimetype': 'application/xml',
        })

    ####################################################
    # Account.edi.format override
    ####################################################

    def _create_invoice_from_xml_tree(self, filename, tree, journal=None):
        self.ensure_one()
        if self.code == 'efff_1' and self._is_ubl(filename, tree) and not self._is_account_edi_ubl_cii_available():
            return self._create_invoice_from_ubl(tree)
        return super()._create_invoice_from_xml_tree(filename, tree, journal=journal)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        self.ensure_one()
        if self.code == 'efff_1' and self._is_ubl(filename, tree) and not self._is_account_edi_ubl_cii_available():
            return self._update_invoice_from_ubl(tree, invoice)
        return super()._update_invoice_from_xml_tree(filename, tree, invoice)

    def _is_compatible_with_journal(self, journal):
        self.ensure_one()
        if self.code != 'efff_1' or self._is_account_edi_ubl_cii_available():
            return super()._is_compatible_with_journal(journal)
        return journal.type == 'sale' and journal.country_code == 'BE'

    def _post_invoice_edi(self, invoices):
        self.ensure_one()
        if self.code != 'efff_1' or self._is_account_edi_ubl_cii_available():
            return super()._post_invoice_edi(invoices)
        res = {}
        for invoice in invoices:
            attachment = self._export_efff(invoice)
            res[invoice] = {'success': True, 'attachment': attachment}
        return res
