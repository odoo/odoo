# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
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
from datetime import date, datetime
from dateutil import relativedelta
from openerp import tools
from openerp.osv import fields, osv


class crm_team(osv.Model):
    _name = "crm.team"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Sales Team"
    _order = "complete_name"
    _period_number = 5

    def get_full_name(self, cr, uid, ids, field_name, arg, context=None):
        return dict(self.name_get(cr, uid, ids, context=context))

    _columns = {
        'name': fields.char('Sales Team', size=64, required=True, translate=True),
        'complete_name': fields.function(get_full_name, type='char', size=256, readonly=True, store=True, string="Full Name"),
        'code': fields.char('Code', size=8),
        'active': fields.boolean('Active', help="If the active field is set to "\
                        "true, it will allow you to hide the sales team without removing it."),
        'change_responsible': fields.boolean('Reassign Escalated', help="When escalating to this team override the salesman with the team leader."),
        'user_id': fields.many2one('res.users', 'Team Leader'),
        'member_ids': fields.many2many('res.users', 'sale_member_rel', 'team_id', 'member_id', 'Team Members'),
        'reply_to': fields.char('Reply-To', size=64, help="The email address put in the 'Reply-To' of all emails sent by Odoo about cases in this sales team"),
        'parent_id': fields.many2one('crm.team', 'Parent Team'),
        'child_ids': fields.one2many('crm.team', 'parent_id', 'Child Teams'),
        'note': fields.text('Description'),
        'working_hours': fields.float('Working Hours', digits=(16, 2)),
        'color': fields.integer('Color Index'),
    }

    _defaults = {
        'active': 1,
    }

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The code of the sales team must be unique !')
    ]

    _constraints = [
        (osv.osv._check_recursion, 'Error ! You cannot create recursive Sales team.', ['parent_id'])
    ]

    def name_get(self, cr, uid, ids, context=None):
        """Overrides orm name_get method"""
        if not isinstance(ids, list):
            ids = [ids]
        res = []
        if not ids:
            return res
        reads = self.read(cr, uid, ids, ['name', 'parent_id'], context)

        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1] + ' / ' + name
            res.append((record['id'], name))
        return res


class res_partner(osv.Model):
    _inherit = 'res.partner'
    _columns = {
        'team_id': fields.many2one('crm.team', 'Sales Team', oldname='section_id'),
    }
