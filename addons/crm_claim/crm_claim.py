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
from crm import crm
import time
from crm import wizard
import binascii
import tools
from tools.translate import _

wizard.mail_compose_message.SUPPORTED_MODELS.append('crm.claim')
CRM_CLAIM_PENDING_STATES = (
    crm.AVAILABLE_STATES[2][0], # Cancelled
    crm.AVAILABLE_STATES[3][0], # Done
    crm.AVAILABLE_STATES[4][0], # Pending
)


class crm_claim(crm.crm_case, osv.osv):
    """
    Crm claim
    """
    _name = "crm.claim"
    _description = "Claim"
    _order = "priority,date desc"
    _inherit = ['mail.thread']
    _columns = {
        'id': fields.integer('ID', readonly=True),
        'name': fields.char('Claim Subject', size=128, required=True),
        'action_next': fields.char('Next Action', size=200),
        'date_action_next': fields.datetime('Next Action Date'),
        'description': fields.text('Description'),
        'resolution': fields.text('Resolution'),
        'create_date': fields.datetime('Creation Date' , readonly=True),
        'write_date': fields.datetime('Update Date' , readonly=True),
        'date_deadline': fields.date('Deadline'),
        'date_closed': fields.datetime('Closed', readonly=True),
        'date': fields.datetime('Claim Date'),
        'ref' : fields.reference('Reference', selection=crm._links_get, size=128),
        'categ_id': fields.many2one('crm.case.categ', 'Category', \
                            domain="[('section_id','=',section_id),\
                            ('object_id.model', '=', 'crm.claim')]"),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
        'type_action': fields.selection([('correction','Corrective Action'),('prevention','Preventive Action')], 'Action Type'),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'user_fault': fields.char('Trouble Responsible', size=64),
        'section_id': fields.many2one('crm.case.section', 'Sales Team', \
                        select=True, help="Sales team to which Case belongs to."\
                                "Define Responsible user and Email account for"\
                                " mail gateway."),
        'company_id': fields.many2one('res.company', 'Company'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'partner_address_id': fields.many2one('res.partner.address', 'Partner Contact', \
                                # domain="[('partner_id','=',partner_id)]"
                                 ),
        'email_cc': fields.text('Watchers Emails', size=252, help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
        'email_from': fields.char('Email', size=128, help="These people will receive email."),
        'partner_phone': fields.char('Phone', size=32),
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('type','=','claim')]"),
        'cause': fields.text('Root Cause'),
        'state': fields.selection(crm.AVAILABLE_STATES, 'State', size=16, readonly=True,
                                  help='The state is set to \'Draft\', when a case is created.\
                                  \nIf the case is in progress the state is set to \'Open\'.\
                                  \nWhen the case is over, the state is set to \'Done\'.\
                                  \nIf the case needs to be reviewed then the state is set to \'Pending\'.'),
        'message_ids': fields.one2many('mail.message', 'res_id', 'Messages', domain=[('model','=',_name)]),
    }

    def stage_next(self, cr, uid, ids, context=None):
        stage = super(crm_claim, self).stage_next(cr, uid, ids, context=context)
        if stage:
            stage_obj = self.pool.get('crm.case.stage').browse(cr, uid, stage, context=context)
            self.message_append(cr, uid, ids, _("Changed Stage to: ") + stage_obj.name)
        return stage

    def stage_previous(self, cr, uid, ids, context=None):
        stage = super(crm_claim, self).stage_previous(cr, uid, ids, context=context)
        if stage:
            stage_obj = self.pool.get('crm.case.stage').browse(cr, uid, stage, context=context)
            self.message_append(cr, uid, ids, _("Changed Stage to: ") + stage_obj.name)
        return stage

    def _get_stage_id(self, cr, uid, context=None):
        """Finds type of stage according to object."""
        if context is None:
            context = {}
        type = context and context.get('stage_type', '')
        stage_ids = self.pool.get('crm.case.stage').search(cr, uid, [('type','=',type),('sequence','>=',1)])
        return stage_ids and stage_ids[0] or False

    _defaults = {
        'user_id': crm.crm_case._get_default_user,
        'partner_id': crm.crm_case._get_default_partner,
        'partner_address_id': crm.crm_case._get_default_partner_address,
        'email_from':crm.crm_case. _get_default_email,
        'state': lambda *a: 'draft',
        'section_id':crm.crm_case. _get_section,
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.case', context=c),
        'priority': lambda *a: crm.AVAILABLE_PRIORITIES[2][0],
        #'stage_id': _get_stage_id,
    }

    def onchange_partner_id(self, cr, uid, ids, part, email=False):
        """This function returns value of partner address based on partner

           :param part: Partner's id
           :param email: ignored
        """
        if not part:
            return {'value': {'partner_address_id': False,
                            'email_from': False,
                            'partner_phone': False,
                            'partner_mobile': False
                            }}
        addr = self.pool.get('res.partner').address_get(cr, uid, [part], ['contact'])
        data = {'partner_address_id': addr['contact']}
        data.update(self.onchange_partner_address_id(cr, uid, ids, addr['contact'])['value'])
        return {'value': data}

    def onchange_partner_address_id(self, cr, uid, ids, add, email=False):
        """This function returns value of partner email based on Partner Address

           :param part: Partner's id
           :param email: ignored
        """
        if not add:
            return {'value': {'email_from': False}}
        address = self.pool.get('res.partner.address').browse(cr, uid, add)
        return {'value': {'email_from': address.email, 'partner_phone': address.phone, 'partner_mobile': address.mobile}}

    def case_open(self, cr, uid, ids, *args):
        """Opens Claim"""
        res = super(crm_claim, self).case_open(cr, uid, ids, *args)
        claims = self.browse(cr, uid, ids)

        for i in xrange(0, len(ids)):
            if not claims[i].stage_id :
                stage_id = self._find_first_stage(cr, uid, 'claim', claims[i].section_id.id or False)
                self.write(cr, uid, [ids[i]], {'stage_id' : stage_id})

        return res

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """Automatically called when new email message arrives"""
        res_id = super(crm_claim,self).message_new(cr, uid, msg, custom_values=custom_values, context=context)
        subject = msg.get('subject')
        body = msg.get('body_text')
        msg_from = msg.get('from')
        priority = msg.get('priority')
        vals = {
            'name': subject,
            'email_from': msg_from,
            'email_cc': msg.get('cc'),
            'description': body,
            'user_id': False,
        }
        if priority:
            vals['priority'] = priority
        vals.update(self.message_partner_by_email(cr, uid, msg.get('from', False)))
        self.write(cr, uid, [res_id], vals, context=context)
        return res_id

    def message_update(self, cr, uid, ids, msg, vals={}, default_act='pending', context=None):
        if isinstance(ids, (str, int, long)):
            ids = [ids]

        res_id = super(crm_claim,self).message_update(cr, uid, msg, context=context)

        if msg.get('priority') in dict(crm.AVAILABLE_PRIORITIES):
            vals['priority'] = msg.get('priority')

        maps = {
            'cost':'planned_cost',
            'revenue': 'planned_revenue',
            'probability':'probability'
        }
        vls = {}
        for line in msg['body_text'].split('\n'):
            line = line.strip()
            res = tools.misc.command_re.match(line)
            if res and maps.get(res.group(1).lower()):
                key = maps.get(res.group(1).lower())
                vls[key] = res.group(2).lower()
        vals.update(vls)

        # Unfortunately the API is based on lists
        # but we want to update the state based on the
        # previous state, so we have to loop:
        for case in self.browse(cr, uid, ids, context=context):
            values = dict(vals)
            if case.state in CRM_CLAIM_PENDING_STATES:
                values.update(state=crm.AVAILABLE_STATES[1][0]) #re-open
            res = self.write(cr, uid, [case.id], values, context=context)
        return res

    def msg_send(self, cr, uid, id, *args, **argv):
        return True

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'claims_ids': fields.one2many('crm.claim', 'partner_id', 'Claims'),
    }

class crm_stage_claim(osv.osv):

    def _get_type_value(self, cr, user, context):
        list = super(crm_stage_claim, self)._get_type_value(cr, user, context)
        list.append(('claim','Claim'))
        return list

    _inherit = "crm.case.stage"
    _columns = {
            'type': fields.selection(_get_type_value, 'Type'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
