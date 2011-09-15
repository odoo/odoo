# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
from base.ir import ir_edi
from tools.translate import _

class account_invoice(osv.osv, ir_edi.edi):
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
                'reference': True,
                'amount_untaxed': True,
                'amount_tax': True,
                'amount_total': True,
                'reconciled': True,
                'date_invoice': True,
                'date_due': True,
                'partner_id': True,
                'address_invoice_id': True, #only one address needed
                'payment_term': True,
                'currency_id': True,
                'invoice_line': {
                        'name': True,
                        'origin': True,
                        'uos_id': True,
                        'product_id': True,
                        'price_unit': True,
                        'price_subtotal': True,
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
                #'paid': True,
        }
        company_pool = self.pool.get('res.company')
        edi_doc_list = []
        for invoice in records:
            # Get EDI doc based on struct. The result will also contain all metadata fields and attachments.
            edi_doc = super(account_invoice,self).edi_export(cr, uid, [invoice], edi_struct, context)
            if not edi_doc:
                continue
            edi_doc = edi_doc[0]

            # Add company info and address
            edi_company_document = company_pool.edi_export_address(cr, uid, [invoice.company_id], context=context)[invoice.company_id.id]
            edi_doc.update({
                    'company_address': edi_company_document['company_address'],
                    #'company_logo': edi_company_document['company_logo'],#TODO
            })
            edi_doc_list.append(edi_doc)
        return edi_doc_list

    def get_invoice_journal(self, cr, uid, invoice_type, context=None):
        if context is None:
            context = {}
        account_journal_pool = self.pool.get('account.journal')
        journal_context = context.copy()
        journal_context.update({'type':invoice_type})
        journal_id = self._get_journal(cr, uid, context=journal_context)
        journal = False
        if journal_id:
            journal = account_journal_pool.browse(cr, uid, journal_id, context=context)
        return journal

    def get_tax_account(self, cr, uid, invoice_type='out_invoice', context=None):
        #TOCHECK: should select account of output VAT for Customer Invoice and Input VAT for Supplier Invoice
        account_pool = self.pool.get('account.account')
        account_ids = account_pool.search(cr, uid, [('type','<>','view'),('type','<>','income'), ('type', '<>', 'closed')])
        tax_account = False
        if account_ids:
            tax_account = account_pool.browse(cr, uid, account_ids[0])
        return tax_account

    def get_invoice_account(self, cr, uid, partner_id, invoice_type, context=None):
        partner_pool = self.pool.get('res.partner')
        partner = partner_pool.browse(cr, uid, partner_id, context=context)
        if invoice_type in ('out_invoice', 'out_refund'):
            invoice_account = partner.property_account_receivable
        else:
            invoice_account = partner.property_account_payable
        return invoice_account

    def get_product_account(self, cr, uid, product_id, invoice_type, context=None):
        product_pool = self.pool.get('product.product')
        product = product_pool.browse(cr, uid, product_id, context=context)
        account = False
        if invoice_type in ('out_invoice','out_refund'):
            account = product.product_tmpl_id.property_account_income
            if not account:
                account = product.categ_id.property_account_income_categ
        else:
            account = product.product_tmpl_id.property_account_expense
            if not account:
                account = product.categ_id.property_account_expense_categ
        return account

    def edi_import_company(self, cr, uid, edi_document, context=None):
        partner_address_pool = self.pool.get('res.partner.address')
        partner_pool = self.pool.get('res.partner')
        company_pool = self.pool.get('res.company')

        # import company as a new partner, if type==in then supplier=1, else customer=1
        # company_address data used to add address to new partner
        invoice_type = edi_document['type']
        partner_value = {}
        if invoice_type in ('out_invoice', 'in_refund'):
            partner_value.update({'customer': True})
        if invoice_type in ('in_invoice', 'out_refund'):
            partner_value.update({'supplier': True})
        partner_id = company_pool.edi_import_as_partner(cr, uid, edi_document, values=partner_value, context=context)

        # partner_id field is modified to point to the new partner
        res = partner_pool.address_get(cr, uid, [partner_id], ['contact', 'invoice'])
        address_id = res['invoice']
        partner = partner_pool.browse(cr, uid, partner_id, context=context)
        partner_address = partner_address_pool.browse(cr, uid, address_id, context=context)
        edi_document['partner_id'] = self.edi_m2o(cr, uid, partner, context=context)
        edi_document['address_invoice_id'] = self.edi_m2o(cr, uid, partner_address, context=context)
        del edi_document['company_id']
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
        
        #import company as a new partner
        partner_id = self.edi_import_company(cr, uid, edi_document, context=context)

        # change type: out_invoice'<->'in_invoice','out_refund'<->'in_refund'
        invoice_type = edi_document['type']
        invoice_type = invoice_type.startswith('in_') and invoice_type.replace('in_','out_') or invoice_type.replace('out_','in_')
        edi_document['type'] = invoice_type

        # Set Account
        invoice_account = self.get_invoice_account(cr, uid, partner_id, invoice_type, context=context)
        edi_document['account_id'] = invoice_account and self.edi_m2o(cr, uid, invoice_account, context=context) or False

        # reference: should contain the value of the 'internal_number'
        edi_document['reference'] = edi_document.get('internal_number', False)
        # reference_type: 'none'
        edi_document['reference_type'] = 'none'

        # internal number: reset to False, auto-generated
        edi_document['internal_number'] = False
        

        # journal_id: should be selected based on type: simply put the 'type' in the context when calling create(), will be selected correctly
        journal = self.get_invoice_journal(cr, uid, invoice_type, context=context)
        edi_document['journal_id'] = journal and  self.edi_m2o(cr, uid, journal, context=context) or False

        # for invoice lines, the account_id value should be taken from the product's default, i.e. from the default category, as it will not be provided.
        for edi_invoice_line in edi_document.get('invoice_line', []):
            product_id = edi_invoice_line.get('product_id', False)
            account = False
            if product_id:
                product_name = product_id and product_id[1]
                product_id = self.edi_import_relation(cr, uid, 'product.product', product_name, context=context)
                account = self.get_product_account(cr, uid, product_id, invoice_type, context=context)
            # TODO: add effect of fiscal position 
            # account = fpos_obj.map_account(cr, uid, fiscal_position_id, account.id)
            edi_invoice_line['account_id'] = account and self.edi_m2o(cr, uid, account, context=context) or False

        # for tax lines, we disconnect from the invoice.line, so all tax lines will be of type 'manual', and default accounts should be picked based
        # on the tax config of the DB where it is imported.
        for edi_tax_line in edi_document.get('tax_line', []):
            tax_account = self.get_tax_account(cr, uid, context=context)
            if tax_account:
                edi_tax_line['account_id'] = self.edi_m2o(cr, uid, tax_account, context=context) 
            edi_tax_line['manual'] = True

        # TODO :=> payment_term: if set, create a default one based on name... 
        return super(account_invoice,self).edi_import(cr, uid, edi_document, context=context)
      
account_invoice()

class account_invoice_line(osv.osv, ir_edi.edi):
    _inherit='account.invoice.line'

account_invoice_line()
class account_invoice_tax(osv.osv, ir_edi.edi):
    _inherit = "account.invoice.tax"

account_invoice_tax()


