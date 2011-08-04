# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from osv import osv, fields

class account_tax_generate(osv.osv_memory):
    _name = 'account.tax.generate'
    _description = 'Tax Generate'

    def _get_templates(self, cr, uid, context=None):
        return self.pool.get('account.tax.template').search(cr, uid, [('installable', '=', False)], context=context)

    _columns = {
        'template_ids': fields.many2many('account.tax.template', 'tax_template_rel', 'wizard_id', 'template_id', 'Taxes Template', domain = [('installable','=',False)]),
    }

    _defaults = {
        'template_ids': _get_templates,
    }

    def tax_generate(self, cr, uid, ids, context=None):
        for tax in self.browse(cr, uid, ids, context=context)[0].template_ids:
            vals_tax = {
                'name':tax.name,
                'sequence': tax.sequence,
                'amount':tax.amount,
                'type':tax.type,
                'applicable_type': tax.applicable_type,
                'domain':tax.domain,
                'parent_id': tax.parent_id and ((tax.parent_id.id in tax_template_ref) and tax_template_ref[tax.parent_id.id]) or False,
                'child_depend': tax.child_depend,
                'python_compute': tax.python_compute,
                'python_compute_inv': tax.python_compute_inv,
                'python_applicable': tax.python_applicable,
                'base_code_id': tax.base_code_id and ((tax.base_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.base_code_id.id]) or False,
                'tax_code_id': tax.tax_code_id and ((tax.tax_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.tax_code_id.id]) or False,
                'base_sign': tax.base_sign,
                'tax_sign': tax.tax_sign,
                'ref_base_code_id': tax.ref_base_code_id and ((tax.ref_base_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.ref_base_code_id.id]) or False,
                'ref_tax_code_id': tax.ref_tax_code_id and ((tax.ref_tax_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.ref_tax_code_id.id]) or False,
                'ref_base_sign': tax.ref_base_sign,
                'ref_tax_sign': tax.ref_tax_sign,
                'include_base_amount': tax.include_base_amount,
                'description':tax.description,
                'company_id': self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id,
                'type_tax_use': tax.type_tax_use,
                'price_include': tax.price_include
            }
            new_tax = self.pool.get('account.tax').create(cr, uid, vals_tax)
            self.pool.get('account.tax.template').write(cr, uid , [tax.id], {'installable': True})
        return {}

account_tax_generate()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
