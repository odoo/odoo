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

import openerp
from openerp.addons.crm import crm
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import html2plaintext


class crm_claim_stage(osv.Model):
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
        'name': fields.char('Stage Name', required=True, translate=True),
        'sequence': fields.integer('Sequence', help="Used to order stages. Lower is better."),
        'team_ids':fields.many2many('crm.team', 'crm_team_claim_stage_rel', 'stage_id', 'team_id', string='Teams',
                        help="Link between stages and sales teams. When set, this limitate the current stage to the selected sales teams."),
        'case_default': fields.boolean('Common to All Teams',
                        help="If you check this field, this stage will be proposed by default on each sales team. It will not assign this stage to existing teams."),
        'fold': fields.boolean('Folded in Kanban View',
                               help='This stage is folded in the kanban view when'
                               'there are no records in that stage to display.'),
        'on_followup':fields.boolean('Follow-up')
    }

    _defaults = {
        'sequence': lambda *args: 1,
        'on_followup': False
    }

class crm_claim(osv.osv):
    """ Crm claim
    """
    _name = "crm.claim"
    _description = "Claim"
    _order = "priority, date desc"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    def _get_default_stage_id(self, cr, uid, context=None):
        """ Gives default stage_id """
        if context is None:
            context = {}
        team_id = context.get('default_team_id')
        return self.stage_find(cr, uid, [], team_id, [('sequence', '=', '1')], context=context)

    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        access_rights_uid = access_rights_uid or uid
        Stage = self.pool['crm.claim.stage']
        order = Stage._order
        # lame hack to allow reverting search, should just work in the trivial case
        if read_group_order == 'stage_id desc':
            order = "%s desc" % order
        # retrieve team_id from the context and write the domain
        # - ('id', 'in', 'ids'): add columns that should be present
        # - OR ('case_default', '=', True), ('fold', '=', False): add default columns that are not folded
        # - OR ('team_ids', 'in', team_id), ('fold', '=', False) if team_id: add team columns that are not folded
        search_domain = []
        team_id = context.get('default_team_id')
        if team_id:
            search_domain += ['|', ('team_ids', '=', team_id), ('id', 'in', ids)]
        # perform search
        stage_ids = Stage._search(cr, uid, search_domain, order=order, access_rights_uid=access_rights_uid, context=context)
        result = Stage.name_get(cr, access_rights_uid, stage_ids, context=context)
        # restore order of the search
        result.sort(lambda x,y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

        fold = {}
        for stage in Stage.browse(cr, access_rights_uid, stage_ids, context=context):
            fold[stage.id] = stage.fold or False
        return result, fold

    def action_calendar_followup(self, cr, uid, ids, context=None):
        action = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'calendar', 'action_calendar_event', context)
        action['context'] = {
           'search_default_mymeetings': 1
        }
        return action

    _columns = {
        'id': fields.integer('ID', readonly=True),
        'name': fields.char('Claim Subject', required=True),
        'active': fields.boolean('Active'),
        'action_next': fields.char('Next Action'),
        'date_action_next': fields.datetime('Next Action Date'),
        'description': fields.text('Description'),
        'resolution': fields.text('Resolution'),
        'create_date': fields.datetime('Creation Date' , readonly=True),
        'write_date': fields.datetime('Update Date' , readonly=True),
        'date_deadline': fields.date('Deadline'),
        'date_closed': fields.datetime('Closed', readonly=True),
        'date': fields.datetime('Claim Date', select=True),
        'ref': fields.reference('Subject', selection=openerp.addons.base.res.res_request.referencable_models),
        'categ_id': fields.many2one('crm.claim.category', 'Category'),
        'priority': fields.selection([('0','Normal'), ('1','High')], 'Priority'),
        'type_action': fields.selection([('correction','Corrective Action'),('prevention','Preventive Action')], 'Action Type'),
        'user_id': fields.many2one('res.users', 'Assigned to', track_visibility='always'),
        'user_fault': fields.char('Trouble Responsible'),
        'team_id': fields.many2one('crm.team', 'Sales Team', oldname='section_id',\
                        select=True, help="Responsible sales team."\
                                " Define Responsible user and Email account for"\
                                " mail gateway."),
        'company_id': fields.many2one('res.company', 'Company'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'email_cc': fields.text('Watchers Emails', size=252, help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
        'email_from': fields.char('Email', size=128, help="Destination email for email gateway."),
        'mobile': fields.char('Mobile'),
        'partner_phone': fields.char('Phone'),
        'stage_id': fields.many2one ('crm.claim.stage', 'Stage', track_visibility='onchange',
                domain="['|', ('team_ids', '=', team_id), ('case_default', '=', True)]"),
        'cause': fields.text('Root Cause'),
        'color': fields.integer('Color Index'),
        'attachment_ids': fields.one2many('ir.attachment', 'res_id', domain=lambda self: [('res_model', '=', self._name)], auto_join=True, string='Documents'),
        'phonecall_ids': fields.one2many('crm.phonecall','claim_id', string='Phonecalls'),
        'meeting_ids': fields.one2many('calendar.event', 'claim_id', 'Meetings'),
        'followup_ids': fields.one2many('calendar.event', 'claim_id', 'Follow-up'),
        'kanban_state': fields.selection([('normal', 'Normal'),('blocked', 'Blocked'),('done', 'Ready for next stage')], 'Kanban State',
                                         track_visibility='onchange',
                                         help="A Cliam's kanban state indicates special situations affecting it:\n"
                                              " * Normal is the default situation\n"
                                              " * Blocked indicates something is preventing the progress of this issue\n"
                                              " * Ready for next stage indicates the claim is ready to be pulled to the next stage",
                                         required=False),
    }

    _defaults = {
        'user_id': lambda s, cr, uid, c: uid,
        'team_id': lambda s, cr, uid, context: context.get('default_team_id'),
        'date': fields.datetime.now,
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.case', context=c),
        'priority': '1',
        'active': lambda *a: 1,
        'kanban_state': 'normal',
        'stage_id': lambda s, cr, uid, context: s._get_default_stage_id(cr, uid, context)
    }
    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }

    def action_get_attachment_view(self, cr, uid, ids, context=None):
        action = self.pool['ir.actions.act_window'].for_xml_id(cr, uid, 'base', 'action_attachment')
        action['context'] = {'default_res_model': self._name, 'default_res_id': ids[0]}
        action['domain'] = str(['&', ('res_model', '=', self._name), ('res_id', 'in', ids)])
        return action


    def action_claim_phonecall(self, cr, uid, ids, context=None):
        claim = self.browse(cr, uid, ids[0], context=context)
        action = self.pool['ir.actions.act_window'].for_xml_id(cr, uid, 'crm', 'crm_phonecall_category_phone_incoming0')
        action['context'] = {'default_claim_id': claim.id, 'search_default_claim_id': claim.id, 'default_partner_id': claim.partner_id and claim.partner_id.id or False}
        return action


    def stage_find(self, cr, uid, cases, team_id, domain=[], order='sequence', context=None):
        """ Override of the base.stage method
            Parameter of the stage search taken from the claim:
            - team_id: if set, stages must belong to this team or
              be a default case
        """
        if isinstance(cases, (int, long)):
            cases = self.browse(cr, uid, cases, context=context)
        # collect all team_ids
        team_ids = []
        if team_id:
            team_ids.append(team_id)
        for claim in cases:
            if claim.team_id:
                team_ids.append(claim.team_id.id)
        # OR all team_ids and OR with case_default
        search_domain = []
        if team_ids:
            search_domain += [('|')] * len(team_ids)
            for team_id in team_ids:
                search_domain.append(('team_ids', '=', team_id))
        search_domain.append(('case_default', '=', True))
        # AND with the domain in parameter
        search_domain += list(domain)
        # perform search, return the first found
        stage_ids = self.pool.get('crm.claim.stage').search(cr, uid, search_domain, order=order, context=context)
        if stage_ids:
            return stage_ids[0]
        return False

    def onchange_partner_id(self, cr, uid, ids, partner_id, email=False, context=None):
        """This function returns value of partner address based on partner
           :param email: ignored
        """
        if not partner_id:
            return {'value': {'email_from': False, 'partner_phone': False, 'mobile': False}}
        address = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
        return {'value': {'email_from': address.email, 'partner_phone': address.phone, 'mobile': address.mobile}}

    def create_claim_meeting(self, cr, uid, ids, stage_id, context=None):
        CalendarEvent = self.pool['calendar.event']
        stage = self.pool['crm.claim.stage'].browse(cr, uid, stage_id)
        if not stage.on_followup:
            return 
        for claim in self.browse(cr, uid, ids, context=context):
            CalendarEvent.create(cr, uid, {'name': stage.name, 
                                        'claim_id': claim.id,
                                        'user_id': claim.user_id.id,
                                        'start_datetime': fields.datetime.now(),
                                        'stop_datetime': fields.datetime.now()
                                    }, context=context)     
        return True

    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        if vals.get('team_id') and not context.get('default_team_id'):
            context['default_team_id'] = vals.get('team_id')
        # context: no_log, because subtype already handle this
        create_context = dict(context, mail_create_nolog=True)
        new_claim_id = super(crm_claim, self).create(cr, uid, vals, context=create_context)
        if vals.get('partner_id'):
            self.message_subscribe(cr, uid, [new_claim_id], [vals['partner_id']], context=context)
        if vals.get('stage_id'):
             self.create_claim_meeting(cr, uid, [new_claim_id], vals['stage_id'], context=context)
        return new_claim_id

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('stage_id'):
            if not vals.get('kanban_state'):
                vals['kanban_state'] = 'normal'
            self.create_claim_meeting(cr, uid, ids, vals['stage_id'], context=context)
        if vals.get('partner_id'):
            self.message_subscribe(cr, uid, ids, [vals['partner_id']], context=context)
        return super(crm_claim, self).write(cr, uid, ids, vals, context=context)


    def copy(self, cr, uid, id, default=None, context=None):
        claim = self.browse(cr, uid, id, context=context)
        default = dict(default or {},
            stage_id = self._get_default_stage_id(cr, uid, context=context),
            name = _('%s (copy)') % claim.name)
        return super(crm_claim, self).copy(cr, uid, id, default, context=context)

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
            'partner_id': msg.get('author_id', False),
        }
        if msg.get('priority'):
            defaults['priority'] = msg.get('priority')
        defaults.update(custom_values)
        return super(crm_claim, self).message_new(cr, uid, msg, custom_values=defaults, context=context)

class res_partner(osv.osv):
    _inherit = 'res.partner'
    def _claim_count(self, cr, uid, ids, field_name, arg, context=None):
        Claim = self.pool['crm.claim']
        return {
            partner_id: Claim.search_count(cr,uid, [('partner_id', '=', partner_id)], context=context)  
            for partner_id in ids
        }

    _columns = {
        'claim_count': fields.function(_claim_count, string='# Claims', type='integer'),
    }

class crm_claim_category(osv.Model):
    _name = "crm.claim.category"
    _description = "Category of claim"
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'team_id': fields.many2one('crm.team', 'Sales Team'),
    }
