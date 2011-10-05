# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2011 OpenERP S.A. <http://openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv, orm
from edi import EDIMixin
from tools.translate import _

class account_invoice(osv.osv, EDIMixin):
    _inherit = 'account.invoice'

    def edi_export(self, cr, uid, records, edi_struct=None, context=None):
        """Exports a supplier or customer invoice"""
        edi_struct = {
                'name': True,
                'origin': True,
                'company_id': True, # -> to be changed into partner
                'type': True, # -> reversed at import
                'internal_number': True, # -> reference at import
                'comment': True,
                'date_invoice': True,
                'date_due': True,
                'partner_id': True,
                'address_invoice_id': True, #only one address needed
                'payment_term': True,
                'currency_id': True, # TODO: should perhaps include sample rate + rounding
                'invoice_line': {
                        'name': True,
                        'origin': True,
                        'uos_id': True,
                        'product_id': True,
                        'price_unit': True,
                        'quantity': True,
                        'discount': True,
                        'note': True,
                },
                'tax_line': {
                        'name': True,
                        'base': True,
                        'amount': True,
                        'manual': True,
                        'sequence': True,
                        'base_amount': True,
                        'tax_amount': True,
                },
        }
        res_company = self.pool.get('res.company')
        edi_doc_list = []
        for invoice in records:
            edi_doc = super(account_invoice,self).edi_export(cr, uid, [invoice], edi_struct, context)[0]
            edi_doc.update({
                    'company_address': res_company.edi_export_address(cr, uid, invoice.company_id, context=context),
                    'company_paypal_account': invoice.company_id.paypal_account,
                    #'company_logo': #TODO
            })
            edi_doc_list.append(edi_doc)
        return edi_doc_list

    def _edi_tax_account(self, cr, uid, invoice_type='out_invoice', context=None):
        #TODO/FIXME: should select proper Tax Account
        account_pool = self.pool.get('account.account')
        account_ids = account_pool.search(cr, uid, [('type','<>','view'),('type','<>','income'), ('type', '<>', 'closed')])
        tax_account = False
        if account_ids:
            tax_account = account_pool.browse(cr, uid, account_ids[0])
        return tax_account

    def _edi_invoice_account(self, cr, uid, partner_id, invoice_type, context=None):
        partner_pool = self.pool.get('res.partner')
        partner = partner_pool.browse(cr, uid, partner_id, context=context)
        if invoice_type in ('out_invoice', 'out_refund'):
            invoice_account = partner.property_account_receivable
        else:
            invoice_account = partner.property_account_payable
        return invoice_account

    def _edi_product_account(self, cr, uid, product_id, invoice_type, context=None):
        product_pool = self.pool.get('product.product')
        product = product_pool.browse(cr, uid, product_id, context=context)
        if invoice_type in ('out_invoice','out_refund'):
            account = product.property_account_income or product.categ_id.property_account_income_categ
        else:
            account = product.property_account_expense or product.categ_id.property_account_expense_categ
        return account

    def _edi_import_company(self, cr, uid, edi_document, context=None):
        self._edi_requires_attributes(('company_id','company_address','type'), edi_document)
        res_partner_address = self.pool.get('res.partner.address')
        res_partner = self.pool.get('res.partner')

        # imported company = new partner
        company_id, company_name = edi_document['company_id']
        partner_id = self.edi_import_relation(cr, uid, 'res.partner', company_name,
                                              company_id, context=context)
        invoice_type = edi_document['type']
        partner_value = {}
        if invoice_type in ('out_invoice', 'out_refund'):
            partner_value.update({'customer': True})
        if invoice_type in ('in_invoice', 'in_refund'):
            partner_value.update({'supplier': True})
        partner_id = res_partner.write(cr, uid, [partner_id], partner_value, context=context)

        # imported company_address = new partner address
        address_info = edi_document['company_address']
        address_info['partner_id'] = (company_id, company_name)
        address_info['type'] = 'invoice'
        address_id = res_partner_address.edi_import(cr, uid, address_info, context=context)

        # modify edi_document to refer to new partner
        del edi_document['company_id']
        del edi_document['company_address']
        partner_address = res_partner_address.browse(cr, uid, address_id, context=context)
        edi_document['partner_id'] = (company_id, company_name)
        edi_document['address_invoice_id'] = self.edi_m2o(cr, uid, partner_address, context=context)

        return partner_id


    def edi_import(self, cr, uid, edi_document, context=None):
        """ During import, invoices will import the company that is provided in the invoice as
            a new partner (e.g. supplier company for a customer invoice will be come a supplier
            record for the new invoice.
            Summary of tasks that need to be done:
                - import company as a new partner, if type==in then supplier=1, else customer=1
                - partner_id field is modified to point to the new partner
                - company_address data used to add address to new partner
                - change type: out_invoice'<->'in_invoice','out_refund'<->'in_refund'
                - reference: should contain the value of the 'internal_number'
                - reference_type: 'none'
                - internal number: reset to False, auto-generated
                - journal_id: should be selected based on type: simply put the 'type'
                    in the context when calling create(), will be selected correctly
                - payment_term: if set, create a default one based on name...
                - for invoice lines, the account_id value should be taken from the
                    product's default, i.e. from the default category, as it will not
                    be provided.
                - for tax lines, we disconnect from the invoice.line, so all tax lines
                    will be of type 'manual', and default accounts should be picked based
                    on the tax config of the DB where it is imported.
        """
        if context is None:
            context = {}
        self._edi_requires_attributes(('company_id','company_address','type','invoice_line'), edi_document)

        # change type: out_invoice'<->'in_invoice','out_refund'<->'in_refund'
        invoice_type = edi_document['type']
        invoice_type = invoice_type.startswith('in_') and invoice_type.replace('in_','out_') or invoice_type.replace('out_','in_')
        edi_document['type'] = invoice_type

        #import company as a new partner
        partner_id = self._edi_import_company(cr, uid, edi_document, context=context)

        # Set Account
        invoice_account = self._edi_invoice_account(cr, uid, partner_id, invoice_type, context=context)
        edi_document['account_id'] = invoice_account and self.edi_m2o(cr, uid, invoice_account, context=context) or False

        # reference: should contain the value of the 'internal_number'
        edi_document['reference'] = edi_document.get('internal_number', False)
        # reference_type: 'none'
        edi_document['reference_type'] = 'none'

        # internal number: reset to False, auto-generated
        edi_document['internal_number'] = False

        # journal_id: should be selected based on type: simply put the 'type' in the context when calling create(), will be selected correctly
        context.update(type=invoice_type)

        # for invoice lines, the account_id value should be taken from the product's default, i.e. from the default category, as it will not be provided.
        for edi_invoice_line in edi_document['invoice_line']:
            product_info = edi_invoice_line['product_id']
            product_id = self.edi_import_relation(cr, uid, 'product.product', product_info[1],
                                                  product_info[0], context=context)
            account = self._edi_product_account(cr, uid, product_id, invoice_type, context=context)
            # TODO: could be improved with fiscal positions perhaps
            # account = fpos_obj.map_account(cr, uid, fiscal_position_id, account.id)
            edi_invoice_line['account_id'] = self.edi_m2o(cr, uid, account, context=context) if account else False

        # for tax lines, we disconnect from the invoice.line, so all tax lines will be of type 'manual', and default accounts should be picked based
        # on the tax config of the DB where it is imported.
        tax_account = self._edi_tax_account(cr, uid, context=context)
        tax_account_info = self.edi_m2o(cr, uid, tax_account, context=context)
        for edi_tax_line in edi_document.get('tax_line', []):
            edi_tax_line['account_id'] = tax_account_info
            edi_tax_line['manual'] = True

        return super(account_invoice,self).edi_import(cr, uid, edi_document, context=context)

class account_invoice_line(osv.osv, EDIMixin):
    _inherit='account.invoice.line'

class account_invoice_tax(osv.osv, EDIMixin):
    _inherit = "account.invoice.tax"


