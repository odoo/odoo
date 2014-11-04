# -*- coding: utf-8 -*-

import calendar
from datetime import date
from dateutil import relativedelta
import json

from openerp import tools
from openerp import models, api, fields, _

class crm_team(models.Model):
    _inherit = 'crm.team'
    _inherits = {'mail.alias': 'alias_id'}

    @api.multi
    def _get_opportunities_data(self):

        """ Get opportunities-related data for salesteam kanban view
            monthly_open_leads: number of open lead during the last months
            monthly_planned_revenue: planned revenu of opportunities during the last months
        """
        obj = self.env['crm.lead']
        # res = dict.fromkeys(ids, False)
        month_begin = date.today().replace(day=1)
        date_begin = month_begin - relativedelta.relativedelta(months=self._period_number - 1)
        date_end = month_begin.replace(day=calendar.monthrange(month_begin.year, month_begin.month)
            [1])
        lead_pre_domain = [
        ('create_date', '>=', date_begin.strftime(tools.DEFAULT_SERVER_DATE_FORMAT)),
        ('create_date', '<=', date_end.strftime(tools.DEFAULT_SERVER_DATE_FORMAT)),
        ('type', '=', 'lead')]
        
        opp_pre_domain = [
        ('date_deadline', '>=', date_begin.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)),
        ('date_deadline', '<=', date_end.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)),
        ('type', '=', 'opportunity')]

        for rec in self:
            lead_domain = lead_pre_domain + [('team_id', '=', rec.id)]
            opp_domain = opp_pre_domain + [('team_id', '=', rec.id)]
            rec.monthly_open_leads = json.dumps(self.__get_bar_values(self._cr, self._uid, obj, lead_domain, 
                ['create_date'], 'create_date_count', 'create_date'))
            rec.monthly_planned_revenue = json.dumps(self.__get_bar_values(self._cr, self._uid, obj, opp_domain, 
                ['planned_revenue', 'date_deadline'], 'planned_revenue', 'date_deadline'))

    @api.multi
    def _get_stage_common(self):
        browse_ids = self.env['crm.stage'].search([('case_default', '=', 1)])
        ids = [rec.id for rec in browse_ids]
        return ids

    resource_calendar_id = fields.Many2one('resource.calendar', "Working Time", help="Used to compute open days")
    stage_ids = fields.Many2many(
        comodel_name='crm.stage', 
        relation = 'crm_stage_team_rel', 
        column1='team_id', 
        column2 ='stage_id', 
        string='Stages',
        default=_get_stage_common)
    use_leads = fields.Boolean('Leads',
        help="The first contact you get with a potential customer is a lead you qualify before converting it into a real business opportunity. Check this box to manage leads in this sales team.", default=True)
    use_opportunities = fields.Boolean('Opportunities', 
        help="Check this box to manage opportunities in this sales team.", default=True)
    monthly_open_leads = fields.Char(compute = '_get_opportunities_data', 
        readonly=True, 
        string='Open Leads per Month')
    monthly_planned_revenue = fields.Char(compute = '_get_opportunities_data',
        readonly=True,
        string='Planned Revenue per Month')
    alias_id = fields.Many2one('mail.alias', 'Alias', ondelete="restrict", required=True, help="The email address associated with this team. New emails received will automatically create new leads assigned to the team.")

#TODO: need to migrate
    @api.v7
    def _auto_init(self, cr, context=None):
        """Installation hook to create aliases for all lead and avoid constraint errors."""
        return self.pool.get('mail.alias').migrate_to_alias(cr, self._name, self._table, super(crm_team, self)._auto_init,
            'crm.lead', self._columns['alias_id'], 'name', alias_prefix='Lead+', alias_defaults={}, context=context)

    # @api.model
    # @api.returns('crm.team')
    # def _auto_init(self):
    #     print"-----_auto_init -- V8 -- sale_team.py"
    #     """Installation hook to create aliases for all lead and avoid constraint errors."""
    #     return self.pool['mail.alias'].migrate_to_alias(self._cr, self._name, self._table, super(crm_team, self)._auto_init(),'crm.lead', self._columns['alias_id'], 'name', alias_prefix='Lead+', alias_defaults={}, context=self._context)

    @api.model
    def create(self, vals):
        self = self.with_context(alias_model_name='crm.lead', alias_parent_model_name=self._name)
        team = super(crm_team, self).create(vals)
        # team = self.browse(cr, uid, team_id, context=context)

        # self.pool['mail.alias'].write(self._cr, self._uid, [team.alias_id.id], {'alias_parent_thread_id': team.id, 'alias_defaults': {'team_id': team.id, 'type': 'lead'}}, context=self._context)

        a=team.alias_id.write({'alias_parent_thread_id': team.id, 'alias_defaults': {'team_id': team.id, 'type': 'lead'}})
        return team

    @api.model
    def unlink(self):
        # Cascade-delete mail aliases as well, as they should not exist without the sales team.
        mail_alias = self.pool['mail.alias']
        alias_rec = [team.alias_id for team in self if team.alias_id]
        res = super(crm_team, self).unlink()
        alias_rec.unlink()
        return res