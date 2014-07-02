# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 ITS-1 (<http://www.its1.lv/>)
#                       E-mail: <info@its1.lv>
#                       Address: <Vienibas gatve 109 LV-1058 Riga Latvia>
#                       Phone: +371 66116534
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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class account_tax_code(osv.osv):
    _inherit = 'account.tax.code'

    _columns = {
        'tax_code': fields.char('Tax Code', size=8)
    }

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = self.search(cr, user, ['|',('tax_code',operator,name),('name',operator,name),('code',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

    def name_get(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['tax_code','name','code'], context, load='_classic_write')
        return [(x['id'], (x['code'] and (x['code'] + ' - ') or '') + (x['tax_code'] and (x['tax_code'] + ' ') or '') + x['name']) \
                for x in reads]

account_tax_code()

class account_tax_code_template(osv.osv):
    _inherit = 'account.tax.code.template'

    _columns = {
        'tax_code': fields.char('Tax Code', size=8)
    }

    def generate_tax_code(self, cr, uid, tax_code_root_id, company_id, context=None):
        '''
        This function generates the tax codes from the templates of tax code that are children of the given one passed
        in argument. Then it returns a dictionary with the mappping between the templates and the real objects.

        :param tax_code_root_id: id of the root of all the tax code templates to process
        :param company_id: id of the company the wizard is running for
        :returns: dictionary with the mappping between the templates and the real objects.
        :rtype: dict
        '''
        obj_tax_code_template = self.pool.get('account.tax.code.template')
        obj_tax_code = self.pool.get('account.tax.code')
        tax_code_template_ref = {}
        company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)

        #find all the children of the tax_code_root_id
        children_tax_code_template = tax_code_root_id and obj_tax_code_template.search(cr, uid, [('parent_id','child_of',[tax_code_root_id])], order='id') or []
        for tax_code_template in obj_tax_code_template.browse(cr, uid, children_tax_code_template, context=context):
            vals = {
                'name': (tax_code_root_id == tax_code_template.id) and company.name or tax_code_template.name,
                'code': tax_code_template.code,
                'info': tax_code_template.info,
                'parent_id': tax_code_template.parent_id and ((tax_code_template.parent_id.id in tax_code_template_ref) and tax_code_template_ref[tax_code_template.parent_id.id]) or False,
                'company_id': company_id,
                'sign': tax_code_template.sign,
                'tax_code': tax_code_template.tax_code
            }
            #check if this tax code already exists
            rec_list = obj_tax_code.search(cr, uid, [('name', '=', vals['name']),('code', '=', vals['code']),('company_id', '=', vals['company_id'])], context=context)
            if not rec_list:
                #if not yet, create it
                new_tax_code = obj_tax_code.create(cr, uid, vals)
                #recording the new tax code to do the mapping
                tax_code_template_ref[tax_code_template.id] = new_tax_code
        return tax_code_template_ref

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['tax_code','name','code'], context, load='_classic_write')
        return [(x['id'], (x['code'] and x['code'] + ' - ' or '') + (x['tax_code'] and (x['tax_code'] + ' ') or '') + x['name']) \
                for x in reads]

account_tax_code_template()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

