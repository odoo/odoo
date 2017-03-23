# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil import relativedelta

import openerp
from openerp.osv import fields, osv
from openerp import api

AVAILABLE_STATES = [
    ('draft', 'New'),
    ('cancel', 'Cancelled'),
    ('open', 'In Progress'),
    ('pending', 'Pending'),
    ('done', 'Closed')
]

class lead_test(osv.Model):
    _name = "base.action.rule.lead.test"
    _description = "Action Rule Test"

    _columns = {
        'name': fields.char('Subject', required=True, select=1),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'state': fields.selection(AVAILABLE_STATES, string="Status", readonly=True),
        'active': fields.boolean('Active', required=False),
        'partner_id': fields.many2one('res.partner', 'Partner', ondelete='set null'),
        'date_action_last': fields.datetime('Last Action', readonly=1),
        'line_ids': fields.one2many('base.action.rule.line.test', 'lead_id'),
    }

    _defaults = {
        'state' : 'draft',
        'active' : True,
    }

    customer = openerp.fields.Boolean(related='partner_id.customer', readonly=True, store=True)
    priority = openerp.fields.Boolean()
    deadline = openerp.fields.Boolean(compute='_compute_deadline', store=True)
    is_assigned_to_admin = openerp.fields.Boolean(string='Assigned to admin user')

    @api.depends('priority')
    def _compute_deadline(self):
        for record in self:
            if not record.priority:
                record.deadline = False
            else:
                record.deadline = openerp.fields.Datetime.from_string(record.create_date) + relativedelta.relativedelta(days=3)

    @api.cr_uid_ids_context
    def message_post(self, cr, uid, thread_id, body='', subject=None, message_type='notification', subtype=None, parent_id=False, attachments=None, context=None, **kwargs):
        pass

    def message_subscribe(self, cr, uid, ids, partner_ids=None, channel_ids=None, subtype_ids=None, force=True, context=None):
        pass


class line_test(osv.Model):
    _name = "base.action.rule.line.test"
    _description = "Action Rule Line Test"

    name = openerp.fields.Char()
    lead_id = openerp.fields.Many2one('base.action.rule.lead.test', ondelete='cascade')
    user_id = openerp.fields.Many2one('res.users')
