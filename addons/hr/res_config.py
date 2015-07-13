# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv

class hr_config_settings(osv.osv_memory):
    _name = 'hr.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'module_hr_timesheet_sheet': fields.boolean('Allow timesheets validation by managers',
            help ="""This installs the module hr_timesheet_sheet."""),
        'module_hr_attendance': fields.boolean('Install attendances feature',
            help ="""This installs the module hr_attendance."""),
        'module_hr_timesheet': fields.boolean('Manage timesheets',
            help ="""This installs the module hr_timesheet."""),
        'module_hr_holidays': fields.boolean('Manage holidays, leaves and allocation requests',
            help ="""This installs the module hr_holidays."""),
        'module_hr_expense': fields.boolean('Manage employees expenses',
            help ="""This installs the module hr_expense."""),
        'module_hr_recruitment': fields.boolean('Manage the recruitment process',
            help ="""This installs the module hr_recruitment."""),
        'module_hr_contract': fields.boolean('Record contracts per employee',
            help ="""This installs the module hr_contract."""),
        'module_hr_evaluation': fields.boolean('Organize employees periodic evaluation',
            help ="""This installs the module hr_evaluation."""),
        'module_hr_gamification': fields.boolean('Drive engagement with challenges and badges',
            help ="""This installs the module hr_gamification."""),
        'module_sale_contract': fields.boolean('Allow invoicing based on timesheets (the sale application will be installed)',
            help ="""This installs the module sale_contract, which will install sales management too."""),
        'module_hr_payroll': fields.boolean('Manage payroll',
            help ="""This installs the module hr_payroll."""),
        'module_website_hr_recruitment': fields.boolean('Publish jobs on your website',
            help ="""This installs the module website_hr_recruitment"""),
        'group_hr_attendance': fields.boolean('Track attendances for all employees',
            implied_group='base.group_hr_attendance',
            help="Allocates attendance group to all users."),
    }

    def onchange_hr_timesheet(self, cr, uid, ids, timesheet, context=None):
        """ module_hr_timesheet implies module_hr_attendance """
        if timesheet:
            return {'value': {'module_hr_attendance': True}}
        return {}

    def onchange_hr_attendance(self, cr, uid, ids, attendance, context=None):
        """ module_hr_timesheet implies module_hr_attendance """
        if not attendance:
            return {'value': {'module_hr_timesheet': False,'group_hr_attendance': False}}
        return {}
        
    def onchange_group_hr_attendance(self, cr, uid, ids, hr_attendance, context=None):
        if hr_attendance:
            return {'value': {'module_hr_attendance': True}}
        return {}
