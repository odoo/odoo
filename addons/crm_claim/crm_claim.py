# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp
from openerp.osv import fields, osv
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import html2plaintext


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
    _order = "priority,date desc"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    def _get_default_stage_id(self, cr, uid, context=None):
        """ Gives default stage_id """
        team_id = self.pool['crm.team']._get_default_team_id(cr, uid, context=context)
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
        team_id = self.pool['crm.team']._get_default_team_id(cr, uid, context=context)
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
        action = self.pool['ir.actions.act_window'].for_xml_id(cr, uid, 'calendar', 'action_calendar_event', context=context)
        action['context'] = {
           'search_default_mymeetings': 1,
           'default_claim_id': ids[0],
           'search_default_claim_id': ids[0]
        }
        return action

    def _compute_attachment_number(self, cr, uid, ids, field_name, args, context=None):
        attachment_data = self.pool['ir.attachment'].read_group(cr, uid, [('res_id', 'in', ids), ('res_model', '=', self._name)], ['res_id'], ['res_id'])
        mapped_data = dict([(m['res_id'], m['res_id_count']) for m in attachment_data])
        return mapped_data

    def _compute_meeting_count(self, cr, uid, ids, field_name, args, context=None):
        meeting_data = self.pool['calendar.event'].read_group(cr, uid, [('claim_id', 'in', ids)], ['claim_id'], ['claim_id'])
        mapped_data = dict([(m['claim_id'][0], m['claim_id_count']) for m in meeting_data])
        return mapped_data

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
        'date': fields.date('Claim Date', select=True),
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
        'attachment_count': fields.function(_compute_attachment_number, type='integer', string="Document"),
        'meeting_count': fields.function(_compute_meeting_count, string='Meetings', type='integer'),
        'followup_ids':fields.one2many('crm.claim.followup', 'claim_id', "Follow-up"),
    }

    _defaults = {
        'user_id': lambda s, cr, uid, c: uid,
        'team_id': lambda s, cr, uid, c: s.pool['crm.team']._get_default_team_id(cr, uid, context=c),
        'date': fields.date.today,
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.case', context=c),
        'active': lambda *a: 1,
        'stage_id': lambda s, cr, uid, context: s._get_default_stage_id(cr, uid, context=context)
    }

    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }

    def _track_subtype(self, cr, uid, ids, init_values, context=None):
        record = self.browse(cr, uid, ids[0], context=context)
        if 'stage_id' in init_values and record.stage_id.name == 'Settled':
            return 'crm_claim.mt_claim_settled'
        elif 'stage_id' in init_values and record.stage_id.name == 'Rejected':
            return 'crm_claim.mt_claim_rejected'
        return super(crm_claim, self)._track_subtype(cr, uid, ids, init_values, context=context)

    def action_get_attachment_view(self, cr, uid, ids, context=None):
        IrModelData = self.pool['ir.model.data']
        # Select the view
        kanban_view_id = IrModelData.xmlid_to_res_id(cr, uid, 'mail.view_document_file_kanban')
        res_id = ids and ids[0] or False
        value = {
            'name': _('Attachments'),
            'view_type': 'form',
            'view_mode': 'kanban',
            'res_model': 'ir.attachment',
            'context': "{'default_res_model': '%s','default_res_id': %d, 'create': False}" % (self._name, res_id),
            'domain': str(['&', ('res_model', '=', self._name), ('res_id', 'in', ids)]),
            'views': [(kanban_view_id or False, 'kanban')],
            'type': 'ir.actions.act_window',
            'help': _('''<p>
                    Documents are attached to Crm Claim.</p><p>
                    Send messages or log internal notes with attachments to link
                    documents to your Crm Claim.
                </p>'''),
        }
        return value

    def stage_find(self, cr, uid, cases, team_id, domain=[], order='sequence', context=None):
        """ Override of the base.stage method
            Parameter of the stage search taken from the Claim:
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

    def create_claim_followup(self, cr, uid, ids, stage_id, context=None):
        CrmClaimFollowup = self.pool['crm.claim.followup']
        stage = self.pool['crm.claim.stage'].browse(cr, uid, stage_id, context=context)
        # on_followup: To find a particular stage that is new,settled,rejected
        if not stage.on_followup:
            return False
        for claim in self.browse(cr, uid, ids, context=context):
            CrmClaimFollowup.create(cr, uid, {
                'date': fields.date.today(),
                'claim_id': claim.id,
                'action': stage.name,
                'user_id': claim.user_id.id}, context=context)
        return True

    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        if vals.get('team_id') and not self.pool['crm.team']._get_default_team_id(cr, uid, context=context):
            context['default_team_id'] = vals.get('team_id')
        # context: no_log, because subtype already handle this
        create_context = dict(context, mail_create_nolog=True)
        new_claim_id = super(crm_claim, self).create(cr, uid, vals, context=create_context)
        if vals.get('partner_id'):
            self.message_subscribe(cr, uid, [new_claim_id], [vals['partner_id']], context=context)
        if vals.get('stage_id'):
             self.create_claim_followup(cr, uid, [new_claim_id], vals['stage_id'], context=context)
        return new_claim_id

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('stage_id'):
            self.create_claim_followup(cr, uid, ids, vals['stage_id'], context=context)
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
