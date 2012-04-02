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

from osv import fields, osv
from lxml import etree

class human_resources_configuration(osv.osv_memory):
    _name = 'human.resources.configuration'
    _inherit = 'res.config.settings'
    
    _columns = {
        'module_hr_timesheet_sheet': fields.boolean('Manage Timesheet and Attendances',
                           help ="""It installs the hr_timesheet_sheet module."""),
        'module_hr_holidays': fields.boolean('Manage Holidays',
                           help ="""It installs the hr_holidays module."""),  
        'module_hr_payroll': fields.boolean('Configure Your Payroll Structure',
                           help ="""It installs the hr_payroll module."""),  
        'module_hr_expense': fields.boolean('Manage Employees Expenses',
                           help ="""It installs the hr_expense module."""),
        'module_hr_recruitment': fields.boolean('Manage Recruitment Process',
                           help ="""It installs the hr_payroll module."""),
        'module_hr_contract': fields.boolean('Manage Employees Contracts',
                           help ="""It installs the hr_contract module."""),
        'module_hr_evaluation': fields.boolean('Manage Appraisals Process',
                           help ="""It installs the hr_evaluation module."""),
        'module_l10n_be_hr_payroll': fields.boolean('Allow to change Payroll Rules',
                           help ="""It allow to change payroll Rules."""),                                                                                                               
                }

    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        
        ir_module = self.pool.get('ir.module.module')
        
        payroll_id= ir_module.search(cr, uid, [('name','=','hr_payroll')])
        recruitment_id= ir_module.search(cr, uid, [('name','=','hr_recruitment')])
        timesheet_id= ir_module.search(cr, uid, [('name','=','hr_timesheet_sheet')])
        
        payroll_modle_state = ir_module.browse(cr,uid, payroll_id[0],context=context).state
        recruitment_modle_state = ir_module.browse(cr,uid, recruitment_id[0],context=context).state
        timesheet_modle_state = ir_module.browse(cr,uid, timesheet_id[0],context=context).state
        
        
        res = super(human_resources_configuration, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        doc = etree.XML(res['arch'])
        
        if recruitment_modle_state == 'uninstalled':
            for node in doc.xpath("//group[@name='Recruitment']"):
                node.set('invisible', '1')
            res['arch'] = etree.tostring(doc)
            
        return res

human_resources_configuration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: