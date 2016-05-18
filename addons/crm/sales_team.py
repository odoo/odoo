# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _


class crm_team(osv.Model):
    _inherit = 'crm.team'
    _inherits = {'mail.alias': 'alias_id'}

    def _get_default_stage_ids(self, cr, uid, context=None):
        return [
            (0, 0, {
                'name': _('Incoming'),
                'sequence': 1,
                'probability': 10.0,
                'on_change': True,
                'fold': False,
                'type': 'both',
            }),
            (0, 0, {
                'name': _('Qualified'),
                'sequence': 2,
                'probability': 30.0,
                'on_change': True,
                'fold': False,
                'type': 'opportunity',
            }),
            (0, 0, {
                'name': _('Proposal'),
                'sequence': 3,
                'probability': 70.0,
                'on_change': True,
                'fold': False,
                'type': 'opportunity',
            }),
            (0, 0, {
                'name': _('Negotiation'),
                'sequence': 4,
                'probability': 85.0,
                'on_change': True,
                'fold': False,
                'type': 'opportunity',
            }),
            (0, 0, {
                'name': _('Won'),
                'sequence': 50,
                'probability': 100.0,
                'on_change': True,
                'fold': True,
                'type': 'both',
            })]

    _columns = {
        'resource_calendar_id': fields.many2one('resource.calendar', "Working Time", help="Used to compute open days"),
        'stage_ids': fields.many2many('crm.stage', 'crm_team_stage_rel', 'team_id', 'stage_id', 'Stages'),
        'use_leads': fields.boolean('Leads',
            help="The first contact you get with a potential customer is a lead you qualify before converting it into a real business opportunity. Check this box to manage leads in this sales team."),
        'use_opportunities': fields.boolean('Opportunities', help="Check this box to manage opportunities in this sales team."),
        'alias_id': fields.many2one('mail.alias', 'Alias', ondelete="restrict", required=True, help="The email address associated with this team. New emails received will automatically create new leads assigned to the team."),
    }

    def _auto_init(self, cr, context=None):
        """Installation hook to create aliases for all lead and avoid constraint errors."""
        return self.pool.get('mail.alias').migrate_to_alias(cr, self._name, self._table, super(crm_team, self)._auto_init,
            'crm.lead', self._columns['alias_id'], 'name', alias_prefix='Lead+', alias_defaults={}, context=context)

    _defaults = {
        'stage_ids': _get_default_stage_ids,
        'use_opportunities': True,
    }

    def onchange_use_leads_opportunities(self, cr, uid, ids, use_leads, use_opportunities, context=None):
        if use_leads or use_opportunities:
            return {'value': {}}
        return {'value': {'alias_name': False}}

    def _get_alias_defaults_values(self, cr, uid, ids, context=None):
        res = dict.fromkeys(ids, False)
        is_group_use_lead = self.pool['res.users'].has_group(cr, uid, 'crm.group_use_lead')
        for team in self.browse(cr, uid, ids, context=context):
            alias_defaults = eval(team.alias_defaults)
            alias_defaults.update({
                'type': 'lead' if is_group_use_lead and team.use_leads else 'opportunity',
                'team_id': team.id,
            })
            res[team.id] = {
                'alias_defaults': alias_defaults,
                'alias_parent_thread_id': team.id,
            }
        return res

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        create_context = dict(context, alias_model_name='crm.lead', alias_parent_model_name=self._name)
        generate_alias_name = self.pool['ir.values'].get_default(cr, uid, 'sales.config.settings', 'generate_sales_team_alias')
        if generate_alias_name and not vals.get('alias_name'):
            vals['alias_name'] = vals.get('name')
        team_id = super(crm_team, self).create(cr, uid, vals, context=create_context)
        self.write(cr, uid, [team_id],
                   self._get_alias_defaults_values(cr, uid, [team_id], context=context)[team_id],
                   context=context)
        return team_id

    def write(self, cr, uid, ids, vals, context=None):
        res = super(crm_team, self).write(cr, uid, ids, vals, context=context)
        if vals.get('use_leads') or vals.get('alias_defaults'):
            alias_res = self._get_alias_defaults_values(cr, uid, ids, context=context)
            for team_id, values in alias_res.iteritems():
                super(crm_team, self).write(cr, uid, [team_id], values, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        # Cascade-delete mail aliases as well, as they should not exist without the sales team.
        mail_alias = self.pool.get('mail.alias')
        alias_ids = [team.alias_id.id for team in self.browse(cr, uid, ids, context=context) if team.alias_id]
        res = super(crm_team, self).unlink(cr, uid, ids, context=context)
        mail_alias.unlink(cr, uid, alias_ids, context=context)
        return res

    def action_your_pipeline(self, cr, uid, context=None):
        IrModelData = self.pool['ir.model.data']
        action = IrModelData.xmlid_to_object(cr, uid, 'crm.crm_lead_opportunities_tree_view', context=context).read(['name', 'help', 'res_model', 'target', 'domain', 'context', 'type', 'search_view_id'])
        if not action:
            action = {}
        else:
            action = action[0]

        user_team_id = self.pool['res.users'].browse(cr, uid, uid, context=context).sale_team_id.id
        if not user_team_id:
            user_team_id = self.search(cr, uid, [], context=context, limit=1)
            user_team_id = user_team_id and user_team_id[0] or False
            action['help'] = """<p class='oe_view_nocontent_create'>Click here to add new opportunities</p><p>
    Looks like you are not a member of a sales team. You should add yourself
    as a member of one of the sales team.
</p>"""
            if user_team_id:
                action['help'] += "<p>As you don't belong to any sales team, Odoo opens the first one by default.</p>"

        action_context = eval(action['context'], {'uid': uid})
        if user_team_id:
            action_context.update({
                'default_team_id': user_team_id,
                'search_default_team_id': user_team_id
            })

        tree_view_id = IrModelData.xmlid_to_res_id(cr, uid, 'crm.crm_case_tree_view_oppor')
        form_view_id = IrModelData.xmlid_to_res_id(cr, uid, 'crm.crm_case_form_view_oppor')
        kanb_view_id = IrModelData.xmlid_to_res_id(cr, uid, 'crm.crm_case_kanban_view_leads')
        action.update({
            'views': [
                [kanb_view_id, 'kanban'],
                [tree_view_id, 'tree'],
                [form_view_id, 'form'],
                [False, 'graph'],
                [False, 'calendar'],
                [False, 'pivot']
            ],
            'context': action_context,
        })
        return action
