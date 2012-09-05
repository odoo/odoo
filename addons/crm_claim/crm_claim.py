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

from base_status.base_stage import base_stage
import binascii
from crm import crm
from osv import fields, osv
import time
import tools
from tools.translate import _

CRM_CLAIM_PENDING_STATES = (
    crm.AVAILABLE_STATES[2][0], # Cancelled
    crm.AVAILABLE_STATES[3][0], # Done
    crm.AVAILABLE_STATES[4][0], # Pending
)

class crm_claim_stage(osv.osv):
    """ Model for claim stages. This models the main stages of a claim
        management flow. Main CRM objects (leads, opportunities, project 
        issues, ...) will now use only stages, instead of state and stages.
        Stages are for example used to display the kanban view of records.
    """
    _name = "crm.claim.stage"
    _description = "Claim stages"
    _rec_name = 'name'
    _order = "sequence"

    _columns = {
        'name': fields.char('Stage Name', size=64, required=True, translate=True),
        'sequence': fields.integer('Sequence', help="Used to order stages. Lower is better."),
        'section_ids':fields.many2many('crm.case.section', 'section_claim_stage_rel', 'stage_id', 'section_id', string='Sections',
                        help="Link between stages and sales teams. When set, this limitate the current stage to the selected sales teams."),
        'state': fields.selection(crm.AVAILABLE_STATES, 'State', required=True, help="The related state for the stage. The state of your document will automatically change regarding the selected stage. For example, if a stage is related to the state 'Close', when your document reaches this stage, it will be automatically have the 'closed' state."),
        'case_refused': fields.boolean('Refused stage',
                        help='Refused stages are specific stages for done.'),
        'case_default': fields.boolean('Common to All Teams',
                        help="If you check this field, this stage will be proposed by default on each sales team. It will not assign this stage to existing teams."),
        'fold': fields.boolean('Hide in Views when Empty',
                        help="This stage is not visible, for example in status bar or kanban view, when there are no records in that stage to display."),
    }

    _defaults = {
        'sequence': lambda *args: 1,
        'state': 'draft',
        'fold': False,
        'case_refused': False,
    }

class crm_claim(base_stage, osv.osv):
    """ Crm claim
    """
    _name = "crm.claim"
    _description = "Claim"
    _order = "priority,date desc"
    _inherit = ['mail.thread']
    _mail_compose_message = True
    _columns = {
        'id': fields.integer('ID', readonly=True),
        'name': fields.char('Claim Subject', size=128, required=True),
        'active': fields.boolean('Active'),
        'action_next': fields.char('Next Action', size=200),
        'date_action_next': fields.datetime('Next Action Date'),
        'description': fields.text('Description'),
        'resolution': fields.text('Resolution'),
        'create_date': fields.datetime('Creation Date' , readonly=True),
        'write_date': fields.datetime('Update Date' , readonly=True),
        'date_deadline': fields.date('Deadline'),
        'date_closed': fields.datetime('Closed', readonly=True),
        'date': fields.datetime('Claim Date', select=True),
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
        'email_cc': fields.text('Watchers Emails', size=252, help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
        'email_from': fields.char('Email', size=128, help="These people will receive email."),
        'partner_phone': fields.char('Phone', size=32),
        'stage_id': fields.many2one ('crm.claim.stage', 'Stage',
                        domain="['|', ('section_ids', '=', section_id), ('case_default', '=', True)]"), 
        'cause': fields.text('Root Cause'),
        'state': fields.related('stage_id', 'state', type="selection", store=True,
                selection=crm.AVAILABLE_STATES, string="State", readonly=True,
                help='The state is set to \'Draft\', when a case is created.\
                      If the case is in progress the state is set to \'Open\'.\
                      When the case is over, the state is set to \'Done\'.\
                      If the case needs to be reviewed then the state is \
                      set to \'Pending\'.'),
    }

    _defaults = {
        'user_id':  lambda s, cr, uid, c: s._get_default_user(cr, uid, c),
        'partner_id':  lambda s, cr, uid, c: s._get_default_partner(cr, uid, c),
        'email_from': lambda s, cr, uid, c: s._get_default_email(cr, uid, c),
        'section_id': lambda s, cr, uid, c: s._get_default_section_id(cr, uid, c),
        'date': fields.datetime.now,
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.case', context=c),
        'priority': lambda *a: crm.AVAILABLE_PRIORITIES[2][0],
        'active': lambda *a: 1
    }

    def stage_find(self, cr, uid, cases, section_id, domain=[], order='sequence', context=None):
        """ Override of the base.stage method
            Parameter of the stage search taken from the lead:
            - section_id: if set, stages must belong to this section or
              be a default case
        """
        if isinstance(cases, (int, long)):
            cases = self.browse(cr, uid, cases, context=context)
        # collect all section_ids
        section_ids = []
        if section_id:
            section_ids.append(section_id)
        for claim in cases:
            if claim.section_id:
                section_ids.append(claim.section_id.id)
        # OR all section_ids and OR with case_default
        search_domain = []
        if section_ids:
            search_domain += [('|')] * len(section_ids)
            for section_id in section_ids:
                search_domain.append(('section_ids', '=', section_id))
        search_domain.append(('case_default', '=', True))
        # AND with the domain in parameter
        search_domain += list(domain)
        # perform search, return the first found
        stage_ids = self.pool.get('crm.claim.stage').search(cr, uid, search_domain, order=order, context=context)
        if stage_ids:
            return stage_ids[0]
        return False

    def create(self, cr, uid, vals, context=None):
        obj_id = super(crm_claim, self).create(cr, uid, vals, context)
        self.create_send_note(cr, uid, [obj_id], context=context)
        return obj_id

    def case_refuse(self, cr, uid, ids, context=None):
        """ Mark the case as refused: state=done and case_refused=True """
        for lead in self.browse(cr, uid, ids):
            stage_id = self.stage_find(cr, uid, [lead], lead.section_id.id or False, ['&', ('state', '=', 'done'), ('case_refused', '=', True)], context=context)
            if stage_id:
                self.case_set(cr, uid, [lead.id], values_to_update={}, new_stage_id=stage_id, context=context)
        return self.case_refuse_send_note(cr, uid, ids, context=context)

    def onchange_partner_id(self, cr, uid, ids, part, email=False):
        """This function returns value of partner address based on partner
           :param part: Partner's id
           :param email: ignored
        """
        if not part:
            return {'value': {'email_from': False,
                              'partner_phone': False
                            }
                   }
        address = self.pool.get('res.partner').browse(cr, uid, part)
        return {'value': {'email_from': address.email, 'partner_phone': address.phone}}

    # -------------------------------------------------------
    # Mail gateway
    # -------------------------------------------------------

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None: custom_values = {}
        custom_values.update({
            'name': msg.get('subject') or _("No Subject"),
            'description': msg.get('body_text'),
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
        })
        if msg.get('priority'):
            custom_values['priority'] = msg.get('priority')
        custom_values.update(self.message_partner_by_email(cr, uid, msg.get('from'), context=context))
        return super(crm_claim,self).message_new(cr, uid, msg, custom_values=custom_values, context=context)

    def message_update(self, cr, uid, ids, msg, update_vals=None, context=None):
        """ Overrides mail_thread message_update that is called by the mailgateway
            through message_process.
            This method updates the document according to the email.
        """
        if isinstance(ids, (str, int, long)):
            ids = [ids]
        if update_vals is None: update_vals = {}

        if msg.get('priority') in dict(crm.AVAILABLE_PRIORITIES):
            update_vals['priority'] = msg.get('priority')

        maps = {
            'cost':'planned_cost',
            'revenue': 'planned_revenue',
            'probability':'probability'
        }
        for line in msg['body_text'].split('\n'):
            line = line.strip()
            res = tools.misc.command_re.match(line)
            if res and maps.get(res.group(1).lower()):
                key = maps.get(res.group(1).lower())
                update_vals[key] = res.group(2).lower()

        return  super(crm_claim,self).message_update(cr, uid, ids, msg, update_vals=update_vals, context=context)

    # ---------------------------------------------------
    # OpenChatter methods and notifications
    # ---------------------------------------------------

    def case_get_note_msg_prefix(self, cr, uid, id, context=None):
        """ Override of default prefix for notifications. """
        return 'Claim'

    def create_send_note(self, cr, uid, ids, context=None):
        msg = _('Claim has been <b>created</b>.')
        return self.message_append_note(cr, uid, ids, body=msg, context=context)

    def case_refuse_send_note(self, cr, uid, ids, context=None):
        msg = _('Claim has been <b>refused</b>.')
        return self.message_append_note(cr, uid, ids, body=msg, context=context)

    def stage_set_send_note(self, cr, uid, ids, stage_id, context=None):
        """ Override of the (void) default notification method. """
        stage_name = self.pool.get('crm.claim.stage').name_get(cr, uid, [stage_id], context=context)[0][1]
        return self.message_append_note(cr, uid, ids, body= _("Stage changed to <b>%s</b>.") % (stage_name), context=context)


class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'claims_ids': fields.one2many('crm.claim', 'partner_id', 'Claims'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
