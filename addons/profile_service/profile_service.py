# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
import pooler

class profile_service_config_install_modules_wizard(osv.osv_memory):
    _name='profile.service.config.install_modules_wizard'
    _rec_name = 'crm_configuration'
    _columns = {
        'crm_configuration':fields.boolean('CRM & Calendars', help="This installs the customer relationship features like: prospects and opportunities tracking, shared calendar, jobs tracking, bug tracker, and so on."),
        'project_timesheet':fields.boolean('Timesheets', help="Timesheets allows you to track time and costs spent on different projects, represented by analytic accounts."),
        'hr_timesheet_invoice':fields.boolean('Invoice on Timesheets', help="There are different invoicing methods in OpenERP: from sale orders, from shipping, ... Install this module if you plan to invoice your customers based on time spent on projects."),
        'hr_holidays':fields.boolean('Holidays Management', help="Tracks the full holidays management process, from the employee's request to the global planning."),
        'hr_expense':fields.boolean('Expenses Tracking', help="Tracks the personal expenses process, from the employee expense encoding, to the reimbursement of the employee up to the reinvoicing to the final customer."),
        'project_mrp':fields.boolean('Sales Management', help="Manages quotation and sales orders. It allows you to automatically create and invoice tasks on fixes prices from quotations."),
        'account_budget_crossover':fields.boolean('Analytic Budgets', help="Allows you to manage analytic budgets by journals. This module is used to manage budgets of your projects."),
        'board_document':fields.boolean('Document Management',
                    help= "The Document Management System of Open ERP allows you to store, browse, automatically index, search and preview all kind of documents (internal documents, printed reports, calendar system). It opens an FTP access for the users to easily browse association's document."),
        'project_gtd':fields.boolean('Getting Things Done', help="GTD is a methodology to efficiently organise yourself and your tasks. This module fully integrates GTD principle with OpenERP's project management."),
        'scrum':fields.boolean('Scrum Methodology', help="Scrum is an 'agile development methodology', mainly used in IT projects. It helps you to manage teams, long term roadmaps, sprints, and so on."),
        'base_contact':fields.boolean('Advanced Contacts Management',
            help="Allows you to manage partners (enterprises), addresses of partners " \
                "and contacts of these partners (employee/people). Install this if you plan to manage your relationships with partners and contacts, with contacts having different jobs in different companies."),
        'portal': fields.boolean('Portal',
            help="This module allows you to manage a Portal system."),
        'wiki': fields.boolean('Wiki', 
            help="An integrated wiki content management system. This is really "\
                "usefull to manage FAQ, quality manuals, etc.")
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
                    ids = mod_obj.search(cr, uid, [('name', '=', r)])
                    mod_obj.button_install(cr,uid,ids,context=context)
        cr.commit()
        db, pool = pooler.restart_pool(cr.dbname, update_module=True)
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.actions.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
            }
profile_service_config_install_modules_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

