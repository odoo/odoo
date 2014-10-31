# -*- coding: utf-8 -*-

import calendar
from datetime import date
from dateutil import relativedelta
import json

from openerp import tools
from openerp.osv import fields, osv


class crm_case_section(osv.Model):
    _inherit = 'crm.case.section'
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
            lead_domain = lead_pre_domain + [('section_id', '=', id)]
            opp_domain = opp_pre_domain + [('section_id', '=', id)]
            res[id]['monthly_open_leads'] = json.dumps(self.__get_bar_values(cr, uid, obj, lead_domain, ['create_date'], 'create_date_count', 'create_date', context=context))
            res[id]['monthly_planned_revenue'] = json.dumps(self.__get_bar_values(cr, uid, obj, opp_domain, ['planned_revenue', 'date_deadline'], 'planned_revenue', 'date_deadline', context=context))
        return res

    _columns = {
        'resource_calendar_id': fields.many2one('resource.calendar', "Working Time", help="Used to compute open days"),
        'stage_ids': fields.many2many('crm.case.stage', 'section_stage_rel', 'section_id', 'stage_id', 'Stages'),
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
        return self.pool.get('mail.alias').migrate_to_alias(cr, self._name, self._table, super(crm_case_section, self)._auto_init,
            'crm.lead', self._columns['alias_id'], 'name', alias_prefix='Lead+', alias_defaults={}, context=context)

    def _get_stage_common(self, cr, uid, context):
        ids = self.pool.get('crm.case.stage').search(cr, uid, ['|', ('default','=','link'), ('default','=','copy')], context=context)
        return ids

    _defaults = {
        'stage_ids': _get_stage_common,
        'use_leads': True,
        'use_opportunities': True,
    }

    def _compute_stages(self, cr, uid, ids, context=None):
        new_ids = []
        stage_type_obj = self.pool.get('crm.case.stage')
        stage_ids = stage_type_obj.search_read(cr, uid, domain=[('id', 'in', ids), ('default', '=', 'copy')], fields=['id'], context=context)
        for stage in stage_ids:
            new_ids.append(stage_type_obj.copy(cr, uid, stage['id'], default={'default': 'none'}, context=context))
            ids.remove(stage['id'])
        return new_ids + ids

    def _copy_stages(self, cr, uid, stage_ids, context=None):
        """ 
            :param many2many stage_ids: a list of tuples is expected.
                   [[6, 0, Ids], (6, 0, Ids)]
                   [(4,Id), (4,Id), (4,Id)]
        """
        index = 0
        stages = stage_ids
        link_ids = [id[1] for id in stage_ids if id[0]==4]
        link_ids = self._compute_stages(cr, uid, link_ids, context=context)
        for counter, stage in enumerate(stage_ids):
            if stage[0] == 4:
                stages[counter] = (4, link_ids[index])
                index += 1
            if stage[0] == 6:
                ids = self._compute_stages(cr, uid, stage[2], context=context)
                if isinstance(stage, tuple): stages[counter] = (6, 0, ids)
                if isinstance(stage, list):
                    stages[0][2] = ids
        return stages

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if vals.get('stage_ids'):
            vals['stage_ids'] = self._copy_stages(cr, uid, vals['stage_ids'], context=context)
        create_context = dict(context, alias_model_name='crm.lead', alias_parent_model_name=self._name)
        section_id = super(crm_case_section, self).create(cr, uid, vals, context=create_context)
        section = self.browse(cr, uid, section_id, context=context)
        self.pool.get('mail.alias').write(cr, uid, [section.alias_id.id], {'alias_parent_thread_id': section_id, 'alias_defaults': {'section_id': section_id, 'type': 'lead'}}, context=context)
        return section_id

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('stage_ids'):
            vals['stage_ids'] = self._copy_stages(cr, uid, vals['stage_ids'], context=context)
        return super(crm_case_section, self).write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        # Cascade-delete mail aliases as well, as they should not exist without the sales team.
        mail_alias = self.pool.get('mail.alias')
        alias_ids = [team.alias_id.id for team in self.browse(cr, uid, ids, context=context) if team.alias_id]
        res = super(crm_case_section, self).unlink(cr, uid, ids, context=context)
        mail_alias.unlink(cr, uid, alias_ids, context=context)
        return res
