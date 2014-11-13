# -*- coding: utf-8 -*-

import calendar
from datetime import date
from dateutil import relativedelta
import json

from openerp import tools
from openerp.osv import fields, osv


class crm_team(osv.Model):
    _inherit = 'crm.team'
    _inherits = {'mail.alias': 'alias_id'}

    def _get_opportunities_data(self, cr, uid, ids, field_name, arg, context=None):
        """ Get opportunities-related data for salesteam kanban view
            monthly_open_leads: number of open lead during the last months
            monthly_planned_revenue: planned revenu of opportunities during the last months
        """
        obj = self.pool.get('crm.lead')
        res = dict.fromkeys(ids, False)
        month_begin = date.today().replace(day=1)
        date_begin = month_begin - relativedelta.relativedelta(months=self._period_number - 1)
        date_end = month_begin.replace(day=calendar.monthrange(month_begin.year, month_begin.month)[1])
        lead_pre_domain = [('create_date', '>=', date_begin.strftime(tools.DEFAULT_SERVER_DATE_FORMAT)),
                ('create_date', '<=', date_end.strftime(tools.DEFAULT_SERVER_DATE_FORMAT)),
                              ('type', '=', 'lead')]
        opp_pre_domain = [('date_deadline', '>=', date_begin.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)),
                      ('date_deadline', '<=', date_end.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)),
                      ('type', '=', 'opportunity')]
        for id in ids:
            res[id] = dict()
            lead_domain = lead_pre_domain + [('team_id', '=', id)]
            opp_domain = opp_pre_domain + [('team_id', '=', id)]
            res[id]['monthly_open_leads'] = json.dumps(self.__get_bar_values(cr, uid, obj, lead_domain, ['create_date'], 'create_date_count', 'create_date', context=context))
            res[id]['monthly_planned_revenue'] = json.dumps(self.__get_bar_values(cr, uid, obj, opp_domain, ['planned_revenue', 'date_deadline'], 'planned_revenue', 'date_deadline', context=context))
        return res

    _columns = {
        'resource_calendar_id': fields.many2one('resource.calendar', "Working Time", help="Used to compute open days"),
        'stage_ids': fields.many2many('crm.stage', 'crm_team_stage_rel', 'team_id', 'stage_id', 'Stages'),
        'use_leads': fields.boolean('Leads',
            help="The first contact you get with a potential customer is a lead you qualify before converting it into a real business opportunity. Check this box to manage leads in this sales team."),
        'use_opportunities': fields.boolean('Opportunities', help="Check this box to manage opportunities in this sales team."),
        'monthly_open_leads': fields.function(_get_opportunities_data,
            type="char", readonly=True, multi='_get_opportunities_data',
            string='Open Leads per Month'),
        'monthly_planned_revenue': fields.function(_get_opportunities_data,
            type="char", readonly=True, multi='_get_opportunities_data',
            string='Planned Revenue per Month'),
        'alias_id': fields.many2one('mail.alias', 'Alias', ondelete="restrict", required=True, help="The email address associated with this team. New emails received will automatically create new leads assigned to the team."),
    }

    def _auto_init(self, cr, context=None):
        """Installation hook to create aliases for all lead and avoid constraint errors."""
        return self.pool.get('mail.alias').migrate_to_alias(cr, self._name, self._table, super(crm_team, self)._auto_init,
            'crm.lead', self._columns['alias_id'], 'name', alias_prefix='Lead+', alias_defaults={}, context=context)

    def _get_stage_common(self, cr, uid, context):
        ids = self.pool.get('crm.stage').search(cr, uid, [('case_default', '=', 1)], context=context)
        return ids

    _defaults = {
        'stage_ids': _get_stage_common,
        'use_leads': True,
        'use_opportunities': True,
    }

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        create_context = dict(context, alias_model_name='crm.lead', alias_parent_model_name=self._name)
        team_id = super(crm_team, self).create(cr, uid, vals, context=create_context)
        team = self.browse(cr, uid, team_id, context=context)
        self.pool.get('mail.alias').write(cr, uid, [team.alias_id.id], {'alias_parent_thread_id': team_id, 'alias_defaults': {'team_id': team_id, 'type': 'lead'}}, context=context)
        return team_id

    def unlink(self, cr, uid, ids, context=None):
        # Cascade-delete mail aliases as well, as they should not exist without the sales team.
        mail_alias = self.pool.get('mail.alias')
        alias_ids = [team.alias_id.id for team in self.browse(cr, uid, ids, context=context) if team.alias_id]
        res = super(crm_team, self).unlink(cr, uid, ids, context=context)
        mail_alias.unlink(cr, uid, alias_ids, context=context)
        return res
