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

import calendar
from datetime import date, datetime
from dateutil import relativedelta

from openerp import tools
from openerp.osv import fields
from openerp.osv import osv

AVAILABLE_PRIORITIES = [
    ('1', 'Highest'),
    ('2', 'High'),
    ('3', 'Normal'),
    ('4', 'Low'),
    ('5', 'Lowest'),
]

class crm_case_channel(osv.osv):
    _name = "crm.case.channel"
    _description = "Channels"
    _order = 'name'
    _columns = {
        'name': fields.char('Channel Name', size=64, required=True),
        'active': fields.boolean('Active'),
    }
    _defaults = {
        'active': lambda *a: 1,
    }

class crm_case_stage(osv.osv):
    """ Model for case stages. This models the main stages of a document
        management flow. Main CRM objects (leads, opportunities, project
        issues, ...) will now use only stages, instead of state and stages.
        Stages are for example used to display the kanban view of records.
    """
    _name = "crm.case.stage"
    _description = "Stage of case"
    _rec_name = 'name'
    _order = "sequence"

    _columns = {
        'name': fields.char('Stage Name', size=64, required=True, translate=True),
        'sequence': fields.integer('Sequence', help="Used to order stages. Lower is better."),
        'probability': fields.float('Probability (%)', required=True, help="This percentage depicts the default/average probability of the Case for this stage to be a success"),
        'on_change': fields.boolean('Change Probability Automatically', help="Setting this stage will change the probability automatically on the opportunity."),
        'requirements': fields.text('Requirements'),
        'section_ids': fields.many2many('crm.case.section', 'section_stage_rel', 'stage_id', 'section_id', string='Sections',
                        help="Link between stages and sales teams. When set, this limitate the current stage to the selected sales teams."),
        'case_default': fields.boolean('Default to New Sales Team',
                        help="If you check this field, this stage will be proposed by default on each sales team. It will not assign this stage to existing teams."),
        'fold': fields.boolean('Folded in Kanban View',
                               help='This stage is folded in the kanban view when'
                               'there are no records in that stage to display.'),
        'type': fields.selection([('lead', 'Lead'),
                                    ('opportunity', 'Opportunity'),
                                    ('both', 'Both')],
                                    string='Type', size=16, required=True,
                                    help="This field is used to distinguish stages related to Leads from stages related to Opportunities, or to specify stages available for both types."),
    }

    _defaults = {
        'sequence': 1,
        'probability': 0.0,
        'on_change': True,
        'fold': False,
        'type': 'both',
        'case_default': True,
    }


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
            res[id]['monthly_open_leads'] = self.__get_bar_values(cr, uid, obj, lead_domain, ['create_date'], 'create_date_count', 'create_date', context=context)
            res[id]['monthly_planned_revenue'] = self.__get_bar_values(cr, uid, obj, opp_domain, ['planned_revenue', 'date_deadline'], 'planned_revenue', 'date_deadline', context=context)
        return res
    
    _columns = {
        'resource_calendar_id': fields.many2one('resource.calendar', "Working Time", help="Used to compute open days"),
        'stage_ids': fields.many2many('crm.case.stage', 'section_stage_rel', 'section_id', 'stage_id', 'Stages'),
        'use_leads': fields.boolean('Leads',
            help="The first contact you get with a potential customer is a lead you qualify before converting it into a real business opportunity. Check this box to manage leads in this sales team."),
        'monthly_open_leads': fields.function(_get_opportunities_data,
            type="string", readonly=True, multi='_get_opportunities_data',
            string='Open Leads per Month'),
        'monthly_planned_revenue': fields.function(_get_opportunities_data,
            type="string", readonly=True, multi='_get_opportunities_data',
            string='Planned Revenue per Month'),
        'alias_id': fields.many2one('mail.alias', 'Alias', ondelete="restrict", required=True, help="The email address associated with this team. New emails received will automatically ""create new leads assigned to the team."),
    }

    def _get_stage_common(self, cr, uid, context):
        ids = self.pool.get('crm.case.stage').search(cr, uid, [('case_default', '=', 1)], context=context)
        return ids

    _defaults = {
        'stage_ids': _get_stage_common,
        'use_leads': True,
    }

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        create_context = dict(context, alias_model_name='crm.lead', alias_parent_model_name=self._name)
        section_id = super(crm_case_section, self).create(cr, uid, vals, context=create_context)
        section = self.browse(cr, uid, section_id, context=context)
        self.pool.get('mail.alias').write(cr, uid, [section.alias_id.id], {'alias_parent_thread_id': section_id, 'alias_defaults': {'section_id': section_id, 'type': 'lead'}}, context=context)
        return section_id
    
    def unlink(self, cr, uid, ids, context=None):
        # Cascade-delete mail aliases as well, as they should not exist without the sales team.
        mail_alias = self.pool.get('mail.alias')
        alias_ids = [team.alias_id.id for team in self.browse(cr, uid, ids, context=context) if team.alias_id]
        res = super(crm_case_section, self).unlink(cr, uid, ids, context=context)
        mail_alias.unlink(cr, uid, alias_ids, context=context)
        return res

class crm_case_categ(osv.osv):
    """ Category of Case """
    _name = "crm.case.categ"
    _description = "Category of Case"
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'object_id': fields.many2one('ir.model', 'Object Name'),
    }
    def _find_object_id(self, cr, uid, context=None):
        """Finds id for case object"""
        context = context or {}
        object_id = context.get('object_id', False)
        ids = self.pool.get('ir.model').search(cr, uid, ['|',('id', '=', object_id),('model', '=', context.get('object_name', False))])
        return ids and ids[0] or False
    _defaults = {
        'object_id' : _find_object_id
    }

class crm_case_resource_type(osv.osv):
    """ Resource Type of case """
    _name = "crm.case.resource.type"
    _description = "Campaign"
    _rec_name = "name"
    _columns = {
        'name': fields.char('Campaign Name', size=64, required=True, translate=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }

class crm_payment_mode(osv.osv):
    """ Payment Mode for Fund """
    _name = "crm.payment.mode"
    _description = "CRM Payment Mode"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
