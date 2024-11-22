# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class L10n_LatamDocumentType(models.Model):
    _inherit = 'l10n_latam.document.type'

    internal_type = fields.Selection(
        selection_add=[
            ('invoice', 'Invoices'),
            ('invoice_in', 'Purchase Invoices'),
            ('debit_note', 'Debit Notes'),
            ('credit_note', 'Credit Notes'),
            ('receipt_invoice', 'Receipt Invoice'),
            ('stock_picking', 'Stock Delivery'),
        ],
    )
    l10n_cl_active = fields.Boolean(
        'Active in localization', help='This boolean enables document to be included on invoicing')

    def _format_document_number(self, document_number):
        """ Make validation of Import Dispatch Number
          * making validations on the document_number. If it is wrong it should raise an exception
          * format the document_number against a pattern and return it
        """
        self.ensure_one()
        if self.country_id.code != "CL":
            return super()._format_document_number(document_number)

        if not document_number:
            return False

        return document_number.zfill(6)

    def _is_doc_type_vendor(self):
        return self.country_id.code == 'CL' and self.code in ('46', '61')

    def _is_doc_type_export(self):
        return self.code in ['110', '111', '112'] and self.country_id.code == 'CL'

    def _is_doc_type_electronic_ticket(self):
        return self.code in ['39', '41'] and self.country_id.code == 'CL'
