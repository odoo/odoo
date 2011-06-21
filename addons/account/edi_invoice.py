
from osv import fields, osv,orm
from base.ir import ir_edi

class account_invoice(osv.osv,ir_edi.edi):

    _inherit = 'account.invoice'
    #_name = 'edi.invoice'

    def edi_export(self, cr, uid, ids, edi_struct=None, context=None):
        """Exports a supplier or customer invoice"""
        rec_id = [ids[0].id]
        
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
                'currency_id': True,
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
        # Get EDI doc based on this struct. The result will also contain
        # all metadata fields and attachments.
        
        edi_doc = super(account_invoice,self).edi_export(cr, uid, ids, edi_struct, context)
        
        
        for i, invoice in enumerate(self.browse(cr, uid, rec_id, context=context)):
            # add specific data for import
            inv_comp = invoice.company_id
            

            comp_partner = inv_comp.partner_id
            
            comp_partner_addr = comp_partner.address
            
            for address in comp_partner_addr:
                

                edi_doc[i].update({
                        # Add company info and address
                        'company_address': {
                                'street': address.street,
                                'street2': address.street2,
                                'zip': address.zip,
                                'city': address.city,
                                'state_id': self.edi_m2o(cr, uid, address.state_id),
                                'country_id': self.edi_m2o(cr, uid, address.country_id),
                                'email': address.email,
                                'phone': address.phone
                        },
                        # Function fields are not included in normal export
                        #'company_logo': inv_comp.logo,#TODO
                        #'paid': inv_comp.paid, #TODO
                })
        
        return edi_doc
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
                - #payment_term: if set, create a default one based on name...
                - for invoice lines, the account_id value should be taken from the
                    product's default, i.e. from the default category, as it will not
                    be provided.
                - for tax lines, we disconnect from the invoice.line, so all tax lines
                    will be of type 'manual', and default accounts should be picked based
                    on the tax config of the DB where it is imported.    
        """
        # generic implementation!
        
        partner = self.pool.get('res.partner')
        partner_add = self.pool.get('res.partner.address')
        model_data = self.pool.get('ir.model.data')
        product_obj = self.pool.get('product.product')
        product_categ = self.pool.get('product.category')
        acc_invoice = self.pool.get('account.invoice')
        company = self.pool.get('res.company')
        tax_id = []
        account_id = []
        partner_id = None
        company_id = None
        if context is None:
            context = {}
        for field in edi_document.keys():
            
            if field == 'type':
                if len(edi_document['invoice_line']):
                	name = edi_document['invoice_line'][0]['product_id'][1]
                else:
                	name = None
                re_ids = product_obj.search(cr,uid,[('name','=',name)])
                if edi_document['type'] == 'out_invoice' or edi_document['type'] == 'out_refund':
                    if re_ids:
                        if product_obj.browse(cr,uid,re_ids)[0].property_account_expense:
                            account_id = product_obj.browse(cr,uid,re_ids)[0].property_account_expense
                            
                        else:
                            account_id = product_categ.browse(cr,uid,re_ids)[0].property_account_expense_categ
                        if product_obj.browse(cr,uid,re_ids)[0].taxes_id:
                            tax_id = product_obj.browse(cr, uid,re_ids)[0].taxes_id
                    if edi_document['type'] == 'out_refund':
                        edi_document['type'] = 'in_refund'
                    else:
                        edi_document['type'] = 'in_invoice'       
                          		
                    
                elif edi_document['type'] == 'in_invoice' or edi_document['type'] == 'in_refund':
                    if re_ids:
                        if product_obj.browse(cr,uid,re_ids)[0].property_account_income:
                            account_id = product_obj.browse(cr,uid,re_ids)[0].property_account_income
                        else:
                            account_id = product_categ.browse(cr,uid,re_ids)[0].property_account_income_categ
                        if product_obj.browse(cr,uid,re_ids)[0].taxes_id:
                            tax_id = product_obj.browse(cr, uid,re_ids)[0].taxes_id
                    if edi_document['type'] == 'in_refund':
                        edi_document['type'] = 'out_refund'
                    else:
                        edi_document['type'] = 'out_invoice'
                    
                if account_id:
                    name_ids = model_data.search(cr, uid, [('model','=',account_id._name),('res_id','=',account_id.id)])
                    if name_ids:
                        xml_id = model_data.browse(cr, uid, name_ids)[0].name
                        db_uuid = ir_edi.safe_unique_id(account_id._name,account_id.id)
                        edi_document['invoice_line'][0]['account_id'] = [db_uuid+':'+xml_id,account_id.name]
                        
                if tax_id:
                    name_ids = model_data.search(cr, uid, [('model','=',tax_id[0]._name),('res_id','=',tax_id[0].id)])
                    
                    if name_ids:
                        xml_id = model_data.browse(cr, uid, name_ids)[0].name
                        db_uuid = ir_edi.safe_unique_id(tax_id[0]._name,tax_id[0].id)
                        edi_document['tax_line'][0]['account_id'] = [db_uuid+':'+xml_id,tax_id[0].name]
                        
                else:
                    if len(edi_document['tax_line']):
                        edi_document['tax_line'][0]['manual'] = True
                    
                res = {}
                part = {}
                comp = {}
                partner_id = partner.search(cr,uid,[('name','=',edi_document['company_id'][1])])
                
                if len(partner_id):
                    
                    browse_partner = partner.browse(cr,uid,partner_id[0])
                    u_id = model_data.search(cr, uid, [('res_id','=',browse_partner.id),('model','=',browse_partner._name)])
                    if len(u_id):
                        company_id = browse_partner.company_id
                        xml_obj = model_data.browse(cr,uid,u_id[0])
                        uuid = ir_edi.safe_unique_id(browse_partner._name,browse_partner.id)
                        db_uuid = '%s:%s' % (uuid,xml_obj.name)
                        part.update({'partner_id':[db_uuid,browse_partner.name]})
                        
                else:
                    company_id = company.create(cr, uid, {'name':edi_document['company_id'][1]})
                    add_id = partner_add.create(cr,uid,edi_document['company_address'])
                    res.update({'name': edi_document['company_id'][1],'supplier': True, 'partner_id': edi_document['partner_id'],'address':add_id}) 
                    partner_id = partner.create(cr,uid,res)
                    
                    browse_partner = partner.browse(cr,uid,partner_id[0])
                    
                    u_id = model_data.search(cr, uid, [('res_id','=',browse_partner.id),('model','=',browse_partner._name)])
                    
                    
                    if len(u_id):
                        
                        xml_obj = model_data.browse(cr,uid,u_id[0])
                        uuid = ir_edi.safe_unique_id(browse_partner._name,browse_partner.id)
                        db_uuid = '%s:%s' % (uuid,xml_obj.name)
                        part.update({'partner_id':[db_uuid,browse_partner.name]})
                
                comp_id = partner.search(cr,uid,[('name','=',edi_document['partner_id'][1])])
               
                if len(comp_id): 
                    
                    browse_partner = partner.browse(cr,uid,comp_id[0])
                    
                    browse_company = company.browse(cr,uid,browse_partner.company_id.id)
                    
                    u_id = u_id = model_data.search(cr, uid, [('res_id','=',browse_company.id),('model','=',browse_company._name)])
                    if len(u_id):
                        
                        xml_obj = model_data.browse(cr,uid,u_id[0])
                        uuid = ir_edi.safe_unique_id(browse_company._name,browse_company.id)
                        db_uuid = '%s:%s' % (uuid,xml_obj.name)
                        comp.update({'company_id':[db_uuid,browse_company.name]})
                        
                del edi_document['partner_id']
                del edi_document['company_id']
                edi_document.update(part)
                edi_document.update(comp)      
                if len(partner_id):
                    
                    
                    
                    p = self.pool.get('res.partner').browse(cr, uid, partner_id[0])
                    if company_id:
                        if p.property_account_receivable.company_id.id != company_id.id and p.property_account_payable.company_id.id != company_id.id:
                            property_obj = self.pool.get('ir.property')
                            
                            rec_pro_id = property_obj.search(cr,uid,[('name','=','property_account_receivable'),('res_id','=','res.partner,'+str(partner_id)+''),('company_id','=',company_id.id)])
                            pay_pro_id = property_obj.search(cr,uid,[('name','=','property_account_payable'),('res_id','=','res.partner,'+str(partner_id)+''),('company_id','=',company_id)])
                            if not rec_pro_id:
                                rec_pro_id = property_obj.search(cr,uid,[('name','=','property_account_receivable'),('company_id','=',company_id.id)])
                            if not pay_pro_id:
                                pay_pro_id = property_obj.search(cr,uid,[('name','=','property_account_payable'),('company_id','=',company_id.id)])
                            rec_line_data = property_obj.read(cr,uid,rec_pro_id,['name','value_reference','res_id'])
                            pay_line_data = property_obj.read(cr,uid,pay_pro_id,['name','value_reference','res_id'])
                            rec_res_id = rec_line_data and rec_line_data[0].get('value_reference',False) and int(rec_line_data[0]['value_reference'].split(',')[1]) or False
                            pay_res_id = pay_line_data and pay_line_data[0].get('value_reference',False) and int(pay_line_data[0]['value_reference'].split(',')[1]) or False
                            if not rec_res_id and not pay_res_id:
                                raise osv.except_osv(_('Configuration Error !'),
                                    _('Can not find account chart for this company, Please Create account.'))
                            account_obj = self.pool.get('account.account')
                            rec_obj_acc = account_obj.browse(cr, uid, [rec_res_id])
                            pay_obj_acc = account_obj.browse(cr, uid, [pay_res_id])
                            p.property_account_receivable = rec_obj_acc[0]
                            p.property_account_payable = pay_obj_acc[0]
        
                    if edi_document['type'] in ('out_invoice', 'out_refund'):
                        acc_obj = p.property_account_receivable
                    else:
                        acc_obj = p.property_account_payable
                    res_id = model_data.search(cr,uid,[('model','=',acc_obj._name),('res_id','=',acc_obj.id)])
                    if len(res_id):
                        xml_obj = model_data.browse(cr, uid, res_id[0])
                        uuid = ir_edi.safe_unique_id(acc_obj._name,acc_obj.id)
                        db_uuid = '%s:%s' % (uuid,xml_obj.name)
                        edi_document.update({'account_id':[db_uuid,acc_obj.name]})
                        print "account_id",edi_document['account_id']
                edi_document.update({'reference':edi_document['internal_number'],'reference_type' : 'none'})    
                edi_document['internal_number'] = False
                context['type'] = edi_document['type']  
                comp
        del edi_document['company_address']
        
        
        return super(account_invoice,self).edi_import(cr, uid, edi_document)
      
account_invoice()

class account_invoice_line(osv.osv, ir_edi.edi):
    _inherit='account.invoice.line'

account_invoice_line()
class account_invoice_tax(osv.osv, ir_edi.edi):
    _inherit = "account.invoice.tax"

account_invoice_tax()
