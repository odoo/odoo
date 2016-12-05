# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError

import copy
import base64

from lxml import etree
from StringIO import StringIO
from tempfile import NamedTemporaryFile
from PyPDF2 import PdfFileWriter, PdfFileReader

UBL_NAMESPACES = {
    'cac': '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}',
    'cbc': '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}',
}

''' UBL_NS_REFACTORING is used to restore the right namespaces inside the xml.
This method is necessary when using Qweb because the <t></t> elements cause some 
troubles when some namespaces are specified to etree. So, to avoid this problem,
the namespaces are encoded with a prefix in each tag and can be replaced as a namespace definition
after the Qweb rendering. In this case, the prefix is 'cbc__' or 
'cac__' and is replaced by 'cbc:' or 'cac:' respectively.
'''
UBL_NS_REFACTORING = {
    'cbc__': 'cbc',
    'cac__': 'cac',
}

class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'

    ubl_doc_ref = fields.Binary(
        string='The document reference content as binary',
        help='contains the report as .pdf to embed in the document reference node for e-fff (UBL)',
        readonly=True)

    @api.multi
    def prepare_pdf(self, values=None):
        # We need to save this content as field because the report is generated only once.
        if values:
            for record in self:
                if not record.ubl_doc_ref:
                    record.ubl_doc_ref = values['datas']
        return super(AccountInvoice, self).prepare_pdf(values=values)

    @api.multi
    def get_edi_filenames_BE(self):
        ''' The filename for e-fff doesn't seem to have an official pattern, so
        this filename is defined arbitrarily.
        '''
        return [('%s-UBL-Invoice-2.1.xml' % self.number).replace('/', '')]

    @api.model
    def generate_edi_BE(self):
        ''' Generate the EDI file for belgium,
        following the UBL protocol e-fff
        '''
        filename = self.get_edi_filenames_BE()[0]
        values = self._create_ubl_values_BE()
        qweb = self.env['ir.qweb']
        content = qweb.render('account_ubl.ubl_invoice_e_fff', values=values)
        
        # TEMP: refactoring namespaces
        for key, value in UBL_NS_REFACTORING.items():
            content = content.replace(key, value + ':')

        # Build main tree
        tree = tools.str_as_tree(content)

        # A copy of the tree is generated but without the AdditionalDocumentReference block 
        tree_wo_doc_ref = copy.deepcopy(tree)
        ref_node = tree_wo_doc_ref.find(
            './/' + UBL_NAMESPACES['cac'] + 'AdditionalDocumentReference')
        ref_node_parent = tools.get_parent_node(ref_node)
        ref_node_parent.remove(ref_node)

        # We check if the ubl_doc_ref is not empty.
        # This field is loaded when the report is generated
        if not self.ubl_doc_ref:
            raise UserError(_('Fail during the embedding of original pdf for UBL'))

        # In e-fff protocol, a copy of the document pdf must be embedded to the xml.
        b64_content = base64.decodestring(self.ubl_doc_ref)
        pdf_file = StringIO(b64_content)
        reader = PdfFileReader(pdf_file)
        writer = PdfFileWriter()
        writer.appendPagesFromReader(reader)
        writer.addAttachment(filename, tools.tree_as_str(tree_wo_doc_ref))
        with NamedTemporaryFile(prefix='odoo-ubl-', suffix='.pdf') as f:
            writer.write(f)
            f.seek(0)
            b64_content = f.read()
            f.close()
        b64_content = base64.encodestring(b64_content)

        # Add the binary content to the main tree
        ref_node = tree.find(
            './/' + UBL_NAMESPACES['cbc'] + 'EmbeddedDocumentBinaryObject')
        ref_node.text = b64_content

        # Create attachment
        content = tools.tree_as_str(tree)

        return [self.env['ir.attachment'].create({
            'name': filename,
            'res_id': self.id,
            'res_model': unicode(self._name),
            'datas': base64.encodestring(content),
            'datas_fname': filename,
            'type': 'binary',
            'description': 'e-fff invoice (UBL)',
            })]

    @api.model
    def _create_ubl_values(self):
        ''' Create the common values for UBL.
        '''
        precision_digits = self.env['decimal.precision'].precision_get('Account')

        values = {
            'self': self,
            'currency_name': self.currency_id.name,
            'supplier_party': self.company_id.partner_id.commercial_partner_id,
            'customer_party': self.partner_id.commercial_partner_id
        }

        # TODO add 386 code for advance payment
        values['type_code'] = 380 if self.type == 'out_invoice' else 381
        values['notes'] = [self.comment] if self.comment else []

        # Add infos about payment means. This is required for e-fff.
        # If a bank account is found, the code will be 42, otherwise 31
        values['bank'] = self.journal_id.bank_account_id

        values['amount_untaxed'] = '%0.*f' % (precision_digits, self.amount_untaxed)
        values['amount_total'] = '%0.*f' % (precision_digits, self.amount_total)
        values['residual'] = '%0.*f' % (precision_digits, self.residual)
        values['amount_prepaid'] = '%0.*f' % (precision_digits, self.amount_total - self.residual)

        values['invoice_lines'] = []
        identifier = 0
        for invoice_line_id in self.invoice_line_ids:
            identifier += 1
            iline_values = self._create_ubl_iline_values(invoice_line_id, identifier)
            values['invoice_lines'].append(tools.dict_to_obj(iline_values))
        
        values['line_count'] = len(values['invoice_lines'])

        return values

    @api.model
    def _create_ubl_iline_values(self, invoice_line_id, identifier):
        ''' Create the invoice lines common values for UBL
        '''
        values = {
            'id': identifier,
            'invoice_line_id': invoice_line_id,
            'description': invoice_line_id.edi_description,
            'name': invoice_line_id.edi_product_name,
        }

        values['notes'] = []

        if invoice_line_id.discount:
            values['notes'].append('Discount (%s %)' % invoice_line_id.discount)

        values['taxes'] = []

        res_taxes = invoice_line_id.invoice_line_tax_ids.compute_all(
            invoice_line_id.price_unit, 
            quantity=invoice_line_id.quantity, 
            product=invoice_line_id.product_id, 
            partner=invoice_line_id.invoice_id.partner_id)
        for tax in res_taxes['taxes']:
            tax_values = {'amount_tax': tax['amount']}
            values['taxes'].append(tools.dict_to_obj(tax_values))

        return values

    @api.model
    def _create_ubl_values_BE(self):
        ''' Create the invoice values for UBL following the e-fff protocol.
        '''
        values = self._create_ubl_values()
        values['version_id'] = 2.0
        values['doc_ref_id'] = 'Invoice-' + self.number + '.pdf'

        # The content of attach_binary is added later manually
        values['attach_binary'] = 'None'
        return values            