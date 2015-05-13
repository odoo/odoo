# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp
from openerp.addons.crm import crm
from openerp.osv import fields, osv
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import html2plaintext
from openerp.exceptions import UserError


class crm_helpdesk(osv.osv):
    """ Helpdesk Cases """

    _name = "crm.helpdesk"
    _description = "Helpdesk"
    _order = "id desc"
    _inherit = ['mail.thread']

    _columns = {
            'id': fields.integer('ID', readonly=True),
            'name': fields.char('Name', required=True),
            'active': fields.boolean('Active', required=False),
            'date_action_last': fields.datetime('Last Action', readonly=1),
            'date_action_next': fields.datetime('Next Action', readonly=1),
            'description': fields.text('Description'),
            'create_date': fields.datetime('Creation Date' , readonly=True),
            'write_date': fields.datetime('Update Date' , readonly=True),
            'date_deadline': fields.date('Deadline'),
            'user_id': fields.many2one('res.users', 'Responsible'),
            'team_id': fields.many2one('crm.team', 'Sales Team', oldname='section_id',\
                            select=True, help='Responsible sales team. Define Responsible user and Email account for mail gateway.'),
            'company_id': fields.many2one('res.company', 'Company'),
            'date_closed': fields.datetime('Closed', readonly=True),
            'partner_id': fields.many2one('res.partner', 'Partner'),
            'email_cc': fields.text('Watchers Emails', size=252 , help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
            'email_from': fields.char('Email', size=128, help="Destination email for email gateway"),
            'date': fields.datetime('Date'),
            'ref': fields.reference('Reference', selection=openerp.addons.base.res.res_request.referencable_models),
            'ref2': fields.reference('Reference 2', selection=openerp.addons.base.res.res_request.referencable_models),
            'channel_id': fields.many2one('utm.medium', 'Channel', help="Communication channel."),
            'planned_revenue': fields.float('Planned Revenue'),
            'planned_cost': fields.float('Planned Costs'),
            'priority': fields.selection([('0','Low'), ('1','Normal'), ('2','High')], 'Priority'),
            'probability': fields.float('Probability (%)'),
            'categ_id': fields.many2one('crm.helpdesk.category', 'Category'),
            'duration': fields.float('Duration', states={'done': [('readonly', True)]}),
            'state': fields.selection(
                [('draft', 'New'),
                 ('open', 'In Progress'),
                 ('pending', 'Pending'),
                 ('done', 'Closed'),
                 ('cancel', 'Cancelled')], 'Status', readonly=True, track_visibility='onchange',
                                  help='The status is set to \'Draft\', when a case is created.\
                                  \nIf the case is in progress the status is set to \'Open\'.\
                                  \nWhen the case is over, the status is set to \'Done\'.\
                                  \nIf the case needs to be reviewed then the status is set to \'Pending\'.'),
    }

    _defaults = {
        'active': lambda *a: 1,
        'user_id': lambda s, cr, uid, c: uid,
        'state': lambda *a: 'draft',
        'date': fields.datetime.now,
        'team_id': lambda s, cr, uid, c: s.pool['crm.team']._get_default_team_id(cr, uid, context=c),
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.helpdesk', context=c),
        'priority': '1',
    }

    def on_change_partner_id(self, cr, uid, ids, partner_id, context=None):
        values = {}
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            values = {
                'email_from': partner.email,
            }
        return {'value': values}

    def write(self, cr, uid, ids, values, context=None):
        """ Override to add case management: open/close dates """
        if values.get('state'):
            if values.get('state') in ['draft', 'open'] and not values.get('date_open'):
                values['date_open'] = fields.datetime.now()
            elif values.get('state') == 'close' and not values.get('date_closed'):
                values['date_closed'] = fields.datetime.now()
        return super(crm_helpdesk, self).write(cr, uid, ids, values, context=context)

    # -------------------------------------------------------
    # Mail gateway
    # -------------------------------------------------------

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None:
            custom_values = {}
        desc = html2plaintext(msg.get('body')) if msg.get('body') else ''
        defaults = {
            'name': msg.get('subject') or _("No Subject"),
            'description': desc,
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'user_id': False,
            'partner_id': msg.get('author_id', False),
        }
        defaults.update(custom_values)
        return super(crm_helpdesk, self).message_new(cr, uid, msg, custom_values=defaults, context=context)

class crm_helpdesk_category(osv.Model):
    _name = "crm.helpdesk.category"
    _description = "Helpdesk Category"
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'team_id': fields.many2one('crm.team', 'Sales Team'),
    }

