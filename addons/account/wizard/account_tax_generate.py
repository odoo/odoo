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
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        cr.execute("SELECT description from account_tax where company_id=%s" % (company_id))
        taxes = cr.fetchall()
        tax_names = [x[0] for x in taxes]
        return self.pool.get('account.tax.template').search(cr, uid, [('installable', '=', False), ('description', 'not in', tax_names)], context=context)

    _columns = {
        'template_ids': fields.many2many('account.tax.template', 'tax_template_rel', 'wizard_id', 'template_id', 'Taxes Template', domain = [('installable','=',False)]),
    }

    _defaults = {
        'template_ids': _get_templates,
    }

    def tax_generate(self, cr, uid, ids, context=None):
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        obj_tax_temp = self.pool.get('account.tax.template')
        tax_templates = [x for x in self.browse(cr, uid, ids, context=context)[0].template_ids]
        taxes_ids = obj_tax_temp.generate_tax(cr, uid, tax_templates, {}, company_id, context=context)
        return {}

account_tax_generate()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
