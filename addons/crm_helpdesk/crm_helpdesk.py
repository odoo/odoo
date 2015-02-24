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

import openerp
from openerp.addons.crm import crm
from openerp.osv import fields, osv
from openerp.tools import html2plaintext
from openerp.tools.translate import _
from openerp.exceptions import UserError


class crm_helpdesk(osv.osv):
    """ Helpdesk Cases """

    _name = "crm.helpdesk"
    _description = "Helpdesk"
    _order = "priority, id desc"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _inherits = {'mail.alias': 'alias_id'}

    def _get_default_stage_id(self, cr, uid, context=None):
        """ Gives default stage_id """
        team_id = context.get('default_team_id')
        return self.stage_find(cr, uid, [], team_id, [('sequence', '=', '1')], context=context)

    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        access_rights_uid = access_rights_uid or uid
        Stage = self.pool['crm.helpdesk.stage']
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
            'user_id': fields.many2one('res.users', 'Responsible', track_visibility='always'),
            'team_id': fields.many2one('crm.team', 'Sales Team', oldname='section_id',\
                            select=True, help='Responsible sales team. Define Responsible user and Email account for mail gateway.'),
            'company_id': fields.many2one('res.company', 'Company'),
            'date_closed': fields.datetime('Closed', readonly=True),
            'partner_id': fields.many2one('res.partner', 'Partner'),
            'email_cc': fields.text('Watchers Emails', size=252 , help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
            'email_from': fields.char('Email', size=128, help="Destination email for email gateway"),
            'mobile': fields.char('Mobile'),
            'partner_phone': fields.char('Phone'),
            'date': fields.datetime('Date'),
            'ref': fields.reference('Subject', selection=openerp.addons.base.res.res_request.referencable_models),
            'channel_id': fields.many2one('utm.medium', 'Channel', help="Communication channel."),
            'planned_revenue': fields.float('Planned Revenue'),
            'planned_cost': fields.float('Planned Costs'),
            'priority': fields.selection([('0','Normal'), ('1','high')], 'Priority'),
            'probability': fields.float('Probability (%)'),
            'categ_id': fields.many2one('crm.helpdesk.category', 'Category'),
            'tag_ids': fields.many2many('crm.helpdesk.tag', 'crm_helpdesk_tag_rel', 'helpdesk_id', 'tag_id', 'Tags'),
            'duration': fields.float('Duration', states={'done': [('readonly', True)]}),
            'color': fields.integer('Color Index'),
            'stage_id': fields.many2one('crm.helpdesk.stage', 'Stage', track_visibility='onchange',
                domain="['|', ('team_ids', '=', team_id), ('case_default', '=', True)]"),
            'attachment_ids': fields.one2many('ir.attachment', 'res_id', domain=lambda self: [('res_model', '=', self._name)], auto_join=True, string='Documents'),
            'alias_id': fields.many2one('mail.alias', 'Alias', ondelete="restrict", required=True, help="The email address associated with this team. New emails received will automatically create new helpdesk assigned to the partner."),
            'kanban_state': fields.selection([('normal', 'Normal'),('blocked', 'Blocked'),('done', 'Ready for next stage')], 'Kanban State',
                                         track_visibility='onchange',
                                         help="A helpdesk's kanban state indicates special situations affecting it:\n"
                                              " * Normal is the default situation\n"
                                              " * Blocked indicates something is preventing the progress of this issue\n"
                                              " * Ready for next stage indicates the helpdesk is ready to be pulled to the next stage",
                                         required=False),
    }

    _defaults = {
        'active': lambda *a: 1,
        'user_id': lambda s, cr, uid, c: uid,
        'kanban_state': 'normal',
        'team_id': lambda s, cr, uid, context: context.get('default_team_id'),
        'stage_id': lambda s, cr, uid, context: s._get_default_stage_id(cr, uid, context),
        'date': fields.datetime.now,
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.helpdesk', context=c),
        'priority': '1',
    }

    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }

    def _auto_init(self, cr, context=None):
        """Installation hook to create aliases for all helpdesk and avoid constraint errors."""
        return self.pool['mail.alias'].migrate_to_alias(cr, self._name, self._table, super(crm_helpdesk, self)._auto_init,
            'crm.helpdesk', self._columns['alias_id'], 'name', alias_prefix='helpdesk+', alias_defaults={'helpdesk_id': 'id'}, context=context)

    def action_get_attachment_view(self, cr, uid, ids, context=None):
        action = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'base', 'action_attachment')
        action['context'] = {'default_res_model': self._name, 'default_res_id': ids[0]}
        action['domain'] = str(['&', ('res_model', '=', self._name), ('res_id', 'in', ids)])
        return action

    def stage_find(self, cr, uid, cases, team_id, domain=[], order='sequence', context=None):
        """ Override of the base.stage method
            Parameter of the stage search taken from the helpdesk:
            - team_id: if set, stages must belong to this team or
              be a default case
        """
        if isinstance(cases, (int, long)):
            cases = self.browse(cr, uid, cases, context=context)
        # collect all team_ids
        team_ids = [helpdesk.team_id.id for helpdesk in cases if helpdesk.team_id]
        # OR all team_ids and OR with case_default
        search_domain = []
        if team_ids:
            search_domain += [('|'), ('team_ids', 'in', team_ids)]
        search_domain.append(('case_default', '=', True))
        # AND with the domain in parameter
        search_domain += list(domain)
        # perform search, return the first found
        stage_ids = self.pool['crm.helpdesk.stage'].search(cr, uid, search_domain, order=order, context=context)
        if stage_ids:
            return stage_ids[0]
        return False

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
        if values.get('stage_id'):
            if not values.get( 'kanban_state'):
                values['kanban_state'] = 'normal'
        if values.get('partner_id'):
            self.message_subscribe(cr, uid, ids, [values['partner_id']], context=context)
        return super(crm_helpdesk, self).write(cr, uid, ids, values, context)

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if vals.get('team_id') and not context.get('default_team_id'):
            context['default_team_id'] = vals.get('team_id')
        create_context = dict(context, alias_model_name='crm.helpdesk', alias_parent_model_name=self._name, mail_create_nolog=True)
        new_helpdesk_id = super(crm_helpdesk, self).create(cr, uid, vals, context=create_context)
        helpdesk = self.browse(cr, uid, new_helpdesk_id, context=context)
        self.pool['mail.alias'].write(cr, uid, [helpdesk.alias_id.id], {'alias_parent_thread_id': new_helpdesk_id, 'alias_defaults': {'helpdesk_id': new_helpdesk_id}}, context=create_context)
        if vals.get('partner_id'):
            self.message_subscribe(cr, uid, [new_helpdesk_id], [vals['partner_id']], context=context)
        return new_helpdesk_id

    def unlink(self, cr, uid, ids, context=None):
        alias_ids = [helpdesk.alias_id.id for helpdesk in self.browse(cr, uid, ids, context=context) if helpdesk.alias_id]
        result = super(crm_helpdesk, self).unlink(cr, uid, ids, context=context)
        self.pool['mail.alias'].unlink(cr, uid, alias_ids, context=context)
        return result

    def copy(self, cr, uid, id, default=None, context=None):
        helpdesk = self.browse(cr, uid, id, context=context)
        default = dict(default or {},
            stage_id = self._get_default_stage_id(cr, uid, context=context),
            name = _('%s (copy)') % helpdesk.name)
        return super(crm_helpdesk, self).copy(cr, uid, id, default=default, context=context)

    def case_escalate(self, cr, uid, ids, context=None):
        """ Escalates case to parent level """
        data = {'active': True}
        for case in self.browse(cr, uid, ids, context=context):
            if case.team_id and case.team_id.parent_id:
                parent_id = case.team_id.parent_id
                data['team_id'] = parent_id.id
                if parent_id.change_responsible and parent_id.user_id:
                    data['user_id'] = parent_id.user_id.id
            else:
                raise UserError(_('You can not escalate, you are already at the top level regarding your sales-team category.'))
            self.write(cr, uid, [case.id], data, context=context)
        return True

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
