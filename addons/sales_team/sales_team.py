# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv


class crm_team(osv.Model):
    _name = "crm.team"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Sales Team"
    _order = "name"
    _period_number = 5

    def _get_default_team_id(self, cr, uid, context=None, user_id=None):
        if context is None:
            context = {}
        if user_id is None:
            user_id = uid
        team_ids = self.search(cr, SUPERUSER_ID, ['|', ('user_id', '=', user_id), ('member_ids', 'in', user_id)], limit=1, context=context)
        team_id = team_ids[0] if team_ids else False
        if not team_id and context.get('default_team_id'):
            team_id = context['default_team_id']
        if not team_id:
            team_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'sales_team.team_sales_department')
        return team_id

    _columns = {
        'name': fields.char('Sales Team', size=64, required=True, translate=True),
        'code': fields.char('Code', size=8),
        'active': fields.boolean('Active', help="If the active field is set to "\
                        "false, it will allow you to hide the sales team without removing it."),
        'company_id': fields.many2one('res.company', 'Company'),
        'user_id': fields.many2one('res.users', 'Team Leader'),
        'member_ids': fields.one2many('res.users', 'sale_team_id', 'Team Members'),
        'reply_to': fields.char('Reply-To', size=64, help="The email address put in the 'Reply-To' of all emails sent by Odoo about cases in this sales team"),
        'working_hours': fields.float('Working Hours', digits=(16, 2)),
        'color': fields.integer('Color Index'),
    }

    _defaults = {
        'active': 1,
        'company_id': lambda self, cr, uid, context: self.pool.get('res.company')._company_default_get(cr, uid, 'crm.team', context=context),
    }

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The code of the sales team must be unique !')
    ]

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        context['mail_create_nosubscribe'] = True
        return super(crm_team, self).create(cr, uid, values, context=context)


class res_partner(osv.Model):
    _inherit = 'res.partner'
    _columns = {
        'team_id': fields.many2one('crm.team', 'Sales Team', oldname='section_id'),
    }

class res_users(osv.Model):
    _inherit = 'res.users'
    _columns = {
        'sale_team_id': fields.many2one('crm.team','Sales Team')
    }

