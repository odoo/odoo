# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.xml_utils import check_with_xsd

import base64

from collections import namedtuple


PATH_TO_XSD = 'l10n_be_edi/data/xsd/2.1/maindoc/UBL-Invoice-2.1.xsd'

InvoiceVals = namedtuple('InvoiceVals',
    ['type_code', 'notes', 'supplier_partner_id', 'customer_partner_id', 'bank_id', 'payment_means_code', 'version_id'])
InvoiceLineVals = namedtuple('InvoiceLineVals',
    ['notes', 'taxes'])


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def _l10n_be_edi_get_values(self):
        '''Create values to render the template for the account.invoice.'''
        values = {
            'type_code': 380 if self.type == 'out_invoice' else 381,
            'notes': [self.comment] if self.comment else [],
            'supplier_partner_id': self.company_id.partner_id.commercial_partner_id,
            'customer_partner_id': self.partner_id.commercial_partner_id,
            'bank_id': self.journal_id.bank_account_id,
            'payment_means_code': 42 if self.journal_id.bank_account_id else 31,
            'version_id': 2.1,
        }
        return InvoiceVals(**values)

    @api.multi
    def l10n_be_edi_attachment_name(self):
        return 'UBL-%s.xml' % (self.number or '').replace('/', '')

    @api.multi
    def l10n_be_edi_generate_xml(self, attachment_id=None):
        ''''Generate the e-invoice xml file as attachment.
        :param attachment_id: The attachment to embed.
        '''
        values = {
            'record': self,
            'attachment_binary': attachment_id and attachment_id.datas,
            'document_reference': attachment_id and attachment_id.name
        }
        filename = self.l10n_be_edi_attachment_name()
        content = self.env['ir.qweb'].render('l10n_be_edi.ubl_invoice_e_fff', values=values)
        check_with_xsd(content, PATH_TO_XSD)
        self.env['ir.attachment'].create({
            'name': filename,
            'res_id': self.id,
            'res_model': 'account.invoice',
            'datas': base64.encodestring(content),
            'datas_fname': filename,
            'type': 'binary',
        })


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    l10n_be_edi_description = fields.Char(
        string='EDI description',
        help='Description in one line for EDI documents',
        compute='_compute_l10n_be_edi_description')
    l10n_be_edi_product_name = fields.Char(
        string='EDI product name',
        help='Product name including variants names if necessary',
        compute='_compute_l10n_be_edi_product_name')

    @api.depends('name')
    def _compute_l10n_be_edi_description(self):
        for record in self:
            record.edi_description = record.name.replace('\n', ', ')

    @api.depends('product_id', 'product_id.attribute_value_ids', 'product_id.name')
    def _compute_l10n_be_edi_product_name(self):
        for record in self:
            product_id = record.product_id
            variants = [variant.name for variant in product_id.attribute_value_ids]
            if variants:
                record.edi_product_name = '%s (%s)' % (product_id.name, ', '.join(variants))
            else:
                record.edi_product_name = product_id.name

    @api.multi
    def _l10n_be_edi_get_values(self):
        '''Create values to render the template for the account.invoice.line.'''
        values = {
            'notes': [_('Discount (%s %)') % self.discount] if self.discount else [],
            'taxes': self.invoice_line_tax_ids.compute_all(
                self.price_unit,
                quantity=self.quantity,
                product=self.product_id,
                partner=self.invoice_id.partner_id)['taxes']
        }
        return InvoiceLineVals(**values)
