#-*- coding: utf-8 -*-
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

from base_status.base_stage import base_stage
from crm import crm
from crm import wizard
from osv import fields, osv

wizard.mail_compose_message.SUPPORTED_MODELS.append('crm.fundraising')

class crm_fundraising(base_stage, osv.osv):
    """ Fund Raising Cases """

    _name = "crm.fundraising"
    _description = "Fund Raising"
    _order = "id desc"
    _inherit = ['mail.thread']
    _columns = {
            'id': fields.integer('ID', readonly=True),
            'name': fields.char('Name', size=128, required=True),
            'active': fields.boolean('Active', required=False),
            'date_action_last': fields.datetime('Last Action', readonly=1),
            'date_action_next': fields.datetime('Next Action', readonly=1),
            'description': fields.text('Description'),
            'create_date': fields.datetime('Creation Date' , readonly=True),
            'write_date': fields.datetime('Update Date' , readonly=True),
            'date_deadline': fields.date('Deadline'),
            'user_id': fields.many2one('res.users', 'Responsible'),
            'section_id': fields.many2one('crm.case.section', 'Sales Team', \
                            select=True, help='Sales team to which Case belongs to. Define Responsible user and Email account for mail gateway.'),
            'company_id': fields.many2one('res.company', 'Company'),
            'partner_id': fields.many2one('res.partner', 'Partner'),
            'email_cc': fields.text('Watchers Emails', size=252 , help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
            'email_from': fields.char('Email', size=128, help="These people will receive email."),
            'date_closed': fields.datetime('Closed', readonly=True),
            'date': fields.datetime('Date'),
            'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
            'categ_id': fields.many2one('crm.case.categ', 'Category', \
                                domain="[('section_id','=',section_id),\
                                ('object_id.model', '=', 'crm.fundraising')]"),
            'planned_revenue': fields.float('Planned Revenue'),
            'planned_cost': fields.float('Planned Costs'),
            'probability': fields.float('Probability (%)'),
            'partner_name': fields.char("Employee's Name", size=64),
            'partner_name2': fields.char('Employee Email', size=64),
            'partner_phone': fields.char('Phone', size=32),
            'partner_mobile': fields.char('Mobile', size=32),
            'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('section_ids', '=', section_id)]"), 
            'type_id': fields.many2one('crm.case.resource.type', 'Campaign', \
                             domain="[('section_id','=',section_id)]"),
            'duration': fields.float('Duration'),
            'ref': fields.reference('Reference', selection=crm._links_get, size=128),
            'ref2': fields.reference('Reference 2', selection=crm._links_get, size=128),
            'state': fields.related('stage_id', 'state', type="selection", store=True,
                    selection=crm.AVAILABLE_STATES, string="State", readonly=True,
                    help='The state is set to \'Draft\', when a case is created.\
                        If the case is in progress the state is set to \'Open\'.\
                        When the case is over, the state is set to \'Done\'.\
                        If the case needs to be reviewed then the state is \
                        set to \'Pending\'.'),
            'message_ids': fields.one2many('mail.message', 'res_id', 'Messages', domain=[('model','=',_name)]),
        }

    _defaults = {
            'active': 1,
            'user_id':  lambda s, cr, uid, c: s._get_default_user(cr, uid, c),
            'partner_id':  lambda s, cr, uid, c: s._get_default_partner(cr, uid, c),
            'email_from': lambda s, cr, uid, c: s._get_default_email(cr, uid, c),
            'section_id': lambda s, cr, uid, c: s._get_default_section_id(cr, uid, c),
            'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.case', context=c),
            'priority': crm.AVAILABLE_PRIORITIES[2][0],
            'probability': 0.0,
            'planned_cost': 0.0,
            'planned_revenue': 0.0,
    }

    def stage_find(self, cr, uid, cases, section_id, domain=[], order='sequence', context=None):
        """ Override of the base.stage method
            Parameter of the stage search taken from the lead:
            - type: stage type must be the same or 'both'
            - section_id: if set, stages must belong to this section or
              be a default case
        """
        if isinstance(cases, (int, long)):
            cases = self.browse(cr, uid, cases, context=context)
        domain = list(domain)
        if section_id:
                domain += ['|', ('section_ids', '=', section_id), ('case_default', '=', True)]
        for lead in cases:
            lead_section_id = lead.section_id.id if lead.section_id else None
            if lead_section_id:
                domain += ['|', ('section_ids', '=', lead_section_id), ('case_default', '=', True)]
        stage_ids = self.pool.get('crm.case.stage').search(cr, uid, domain, order=order, context=context)
        if stage_ids:
            return stage_ids[0]
        return False

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """Automatically called when new email message arrives"""
        res_id = super(crm_fundraising,self).message_new(cr, uid, msg, custom_values=custom_values, context=context)
        vals = {
            'name': msg.get('subject'),
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'description': msg.get('body_text'),
        }
        priority = msg.get('priority')
        if priority:
            vals['priority'] = priority
        vals.update(self.message_partner_by_email(cr, uid, msg.get('from')))
        self.write(cr, uid, [res_id], vals, context=context)
        return res_id


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
