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

from osv import fields, osv
import pooler

class profile_accounting_config_install_modules_wizard(osv.osv_memory):
    _name='profile.accounting.config.install_modules_wizard'
    _columns = {
        'name':fields.char('Name', size=64),
        'account_analytic_analysis':fields.boolean('Analytic Accounting'),
        'account_analytic_plans':fields.boolean('Multiple Analytic Plans'),
        'account_payment':fields.boolean('Suppliers Payment Management'),
        'account_asset':fields.boolean('Asset Management'),
        'hr_timesheet_invoice':fields.boolean('Invoice on Analytic Entries'),
        'account_budget':fields.boolean('Budgets', help="Helps you to manage financial and analytic budgets."),
        'board_document':fields.boolean('Document Management',help= "The Document Management System of Open ERP allows you to store, browse, automatically index, search and preview all kind of documents (internal documents, printed reports, calendar system). It opens an FTP access for the users to easily browse association's document."),


    }
    def action_cancel(self,cr,uid,ids,conect=None):
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.actions.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
         }


    def action_install(self, cr, uid, ids, context=None):
        result=self.read(cr,uid,ids)
        mod_obj = self.pool.get('ir.module.module')
        for res in result:
            for r in res:
                if r<>'id' and res[r]:
                    ids += mod_obj.search(cr, uid, [('name', '=', r)])
                    mod_obj.button_install(cr, uid, ids, context=context)
        cr.commit()
        db, pool = pooler.restart_pool(cr.dbname,update_module=True)
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.actions.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
            }


profile_accounting_config_install_modules_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

