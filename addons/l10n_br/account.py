# -*- encoding: utf-8 -*-
#################################################################################
#                                                                               #
# Copyright (C) 2009  Renato Lima - Akretion                                    #
#                                                                               #
#This program is free software: you can redistribute it and/or modify           #
#it under the terms of the GNU Affero General Public License as published by    #
#the Free Software Foundation, either version 3 of the License, or              #
#(at your option) any later version.                                            #
#                                                                               #
#This program is distributed in the hope that it will be useful,                #
#but WITHOUT ANY WARRANTY; without even the implied warranty of                 #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                  #
#GNU General Public License for more details.                                   #
#                                                                               #
#You should have received a copy of the GNU General Public License              #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.          #
#################################################################################

from openerp import pooler
from openerp.osv import fields, osv

TAX_CODE_COLUMNS = {
                    'domain':fields.char('Domain', size=32, 
                                         help="This field is only used if you develop your own module allowing developers to create specific taxes in a custom domain."),
                    'tax_discount': fields.boolean('Discount this Tax in Prince', 
                                                   help="Mark it for (ICMS, PIS, COFINS and others taxes included)."),
                    }

TAX_DEFAULTS = {
                'base_reduction': 0,
                'amount_mva': 0,
                }

class account_tax_code_template(osv.osv):
    """ Add fields used to define some brazilian taxes """
    _inherit = 'account.tax.code.template'
    _columns = TAX_CODE_COLUMNS

    def generate_tax_code(self, cr, uid, tax_code_root_id, company_id, 
                         context=None):
        """This function generates the tax codes from the templates of tax 
        code that are children of the given one passed in argument. Then it 
        returns a dictionary with the mappping between the templates and the 
        real objects.

        :param tax_code_root_id: id of the root of all the tax code templates 
                                 to process.
        :param company_id: id of the company the wizard is running for
        :returns: dictionary with the mappping between the templates and the 
                  real objects.
        :rtype: dict
        """
        obj_tax_code_template = self.pool.get('account.tax.code.template')
        obj_tax_code = self.pool.get('account.tax.code')
        tax_code_template_ref = {}
        company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)

        #find all the children of the tax_code_root_id
        children_tax_code_template = tax_code_root_id and obj_tax_code_template.search(cr, uid, [('parent_id','child_of',[tax_code_root_id])], order='id') or []
        for tax_code_template in obj_tax_code_template.browse(cr, uid, children_tax_code_template, context=context):
            parent_id = tax_code_template.parent_id and ((tax_code_template.parent_id.id in tax_code_template_ref) and tax_code_template_ref[tax_code_template.parent_id.id]) or False
            vals = {
                'name': (tax_code_root_id == tax_code_template.id) and company.name or tax_code_template.name,
                'code': tax_code_template.code,
                'info': tax_code_template.info,
                'parent_id': parent_id,
                'company_id': company_id,
                'sign': tax_code_template.sign,
                'domain': tax_code_template.domain,
                'tax_discount': tax_code_template.tax_discount,
            }
            #check if this tax code already exists
            rec_list = obj_tax_code.search(cr, uid, [('name', '=', vals['name']),
                                                     ('parent_id','=',parent_id),
                                                     ('code', '=', vals['code']),
                                                     ('company_id', '=', vals['company_id'])], context=context)
            if not rec_list:
                #if not yet, create it
                new_tax_code = obj_tax_code.create(cr, uid, vals)
                #recording the new tax code to do the mapping
                tax_code_template_ref[tax_code_template.id] = new_tax_code
        return tax_code_template_ref
    


class account_tax_code(osv.osv):
    """ Add fields used to define some brazilian taxes """
    _inherit = 'account.tax.code'
    _columns = TAX_CODE_COLUMNS


def get_precision_tax():
    def change_digit_tax(cr):
        res = pooler.get_pool(cr.dbname).get('decimal.precision').precision_get(cr, 1, 'Account')
        return (16, res+2)
    return change_digit_tax

class account_tax_template(osv.osv):
    """ Add fields used to define some brazilian taxes """
    _inherit = 'account.tax.template'
    
    _columns = {
               'tax_discount': fields.boolean('Discount this Tax in Prince', 
                                              help="Mark it for (ICMS, PIS e etc.)."),
               'base_reduction': fields.float('Redution', required=True, 
                                              digits_compute=get_precision_tax(), 
                                              help="Um percentual decimal em % entre 0-1."),
               'amount_mva': fields.float('MVA Percent', required=True, 
                                          digits_compute=get_precision_tax(), 
                                          help="Um percentual decimal em % entre 0-1."),
               'type': fields.selection([('percent','Percentage'), 
                                         ('fixed','Fixed Amount'), 
                                         ('none','None'), 
                                         ('code','Python Code'), 
                                         ('balance','Balance'), 
                                         ('quantity','Quantity')], 'Tax Type', required=True,
                                        help="The computation method for the tax amount."),
               }
    _defaults = TAX_DEFAULTS
    
    def _generate_tax(self, cr, uid, tax_templates, tax_code_template_ref, company_id, context=None):
        """
        This method generate taxes from templates.

        :param tax_templates: list of browse record of the tax templates to process
        :param tax_code_template_ref: Taxcode templates reference.
        :param company_id: id of the company the wizard is running for
        :returns:
            {
            'tax_template_to_tax': mapping between tax template and the newly generated taxes corresponding,
            'account_dict': dictionary containing a to-do list with all the accounts to assign on new taxes
            }
        """
        result = super(account_tax_template, self)._generate_tax(cr, uid, 
                                                                 tax_templates, 
                                                                 tax_code_template_ref, 
                                                                 company_id, 
                                                                 context)
        tax_templates = self.browse(cr, uid, result['tax_template_to_tax'].keys(), context)   
        obj_acc_tax = self.pool.get('account.tax')
        for tax_template in tax_templates:
            if tax_template.tax_code_id:
                obj_acc_tax.write(cr, uid, result['tax_template_to_tax'][tax_template.id], {'domain': tax_template.tax_code_id.domain,
                                                                                            'tax_discount': tax_template.tax_code_id.tax_discount})    
        return result
    
    def onchange_tax_code_id(self, cr, uid, ids, tax_code_id, context=None):

        result = {'value': {}}

        if not tax_code_id:
            return result

        obj_tax_code = self.pool.get('account.tax.code.template').browse(cr, uid, tax_code_id)     

        if obj_tax_code:
            result['value']['tax_discount'] = obj_tax_code.tax_discount
            result['value']['domain'] = obj_tax_code.domain

        return result



class account_tax(osv.osv):
    """ Add fields used to define some brazilian taxes """
    _inherit = 'account.tax'
    
    _columns = {
               'tax_discount': fields.boolean('Discount this Tax in Prince', 
                                              help="Mark it for (ICMS, PIS e etc.)."),
               'base_reduction': fields.float('Redution', required=True, 
                                              digits_compute=get_precision_tax(), 
                                              help="Um percentual decimal em % entre 0-1."),
               'amount_mva': fields.float('MVA Percent', required=True, 
                                          digits_compute=get_precision_tax(), 
                                          help="Um percentual decimal em % entre 0-1."),
               'type': fields.selection([('percent','Percentage'), 
                                         ('fixed','Fixed Amount'), 
                                         ('none','None'), 
                                         ('code','Python Code'), 
                                         ('balance','Balance'), 
                                         ('quantity','Quantity')], 'Tax Type', required=True,
                                        help="The computation method for the tax amount."),
               }
    _defaults = TAX_DEFAULTS
    
    def onchange_tax_code_id(self, cr, uid, ids, tax_code_id, context=None):

        result = {'value': {}}

        if not tax_code_id:
            return result
        
        obj_tax_code = self.pool.get('account.tax.code').browse(cr, uid, tax_code_id)      
    
        if obj_tax_code:
            result['value']['tax_discount'] = obj_tax_code.tax_discount
            result['value']['domain'] = obj_tax_code.domain

        return result


