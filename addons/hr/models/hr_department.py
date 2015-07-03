# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from openerp.osv import fields, osv
from openerp.tools.translate import _


class hr_department(osv.osv):
    _name = "hr.department"
    _description = "HR Department"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    def _dept_name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    _columns = {
        'name': fields.char('Department Name', required=True),
        'complete_name': fields.function(_dept_name_get_fnc, type="char", string='Name'),
        'company_id': fields.many2one('res.company', 'Company', select=True, required=False),
        'parent_id': fields.many2one('hr.department', 'Parent Department', select=True),
        'child_ids': fields.one2many('hr.department', 'parent_id', 'Child Departments'),
        'manager_id': fields.many2one('hr.employee', 'Manager', track_visibility='onchange'),
        'member_ids': fields.one2many('hr.employee', 'department_id', 'Members', readonly=True),
        'jobs_ids': fields.one2many('hr.job', 'department_id', 'Jobs'),
        'note': fields.text('Note'),
        'color': fields.integer('Color Index'),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'hr.department', context=c),
    }

    _constraints = [
        (osv.osv._check_recursion, _('Error! You cannot create recursive departments.'), ['parent_id'])
    ]

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context is None:
            context = {}
        reads = self.read(cr, uid, ids, ['name','parent_id'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1]+' / '+name
            res.append((record['id'], name))
        return res

    def create(self, cr, uid, vals, context=None):
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        manager_id = vals.get("manager_id")
        new_id = super(hr_department, self).create(cr, uid, vals, context=context)
        if manager_id:
            employee = self.pool.get('hr.employee').browse(cr, uid, manager_id, context=context)
            if employee.user_id:
                self.message_subscribe_users(cr, uid, [new_id], user_ids=[employee.user_id.id], context=context)
        return new_id

    def write(self, cr, uid, ids, vals, context=None):
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        if isinstance(ids, (int, long)):
            ids = [ids]
        employee_ids = []
        if 'manager_id' in vals:
            manager_id = vals.get("manager_id")
            if manager_id:
                employee = self.pool['hr.employee'].browse(cr, uid, manager_id, context=context)
                if employee.user_id:
                    self.message_subscribe_users(cr, uid, ids, user_ids=[employee.user_id.id], context=context)
            for department in self.browse(cr, uid, ids, context=context):
                employee_ids += self.pool['hr.employee'].search(
                    cr, uid, [
                        ('id', '!=', manager_id),
                        ('department_id', '=', department.id),
                        ('parent_id', '=', department.manager_id.id)
                    ], context=context)
            self.pool['hr.employee'].write(cr, uid, employee_ids, {'parent_id': manager_id}, context=context)
        return super(hr_department, self).write(cr, uid, ids, vals, context=context)
