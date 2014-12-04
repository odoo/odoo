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

from openerp.osv import osv, fields
from openerp.http import request

AVAILABLE_PRIORITIES = [
    ('0', 'Normal'),
    ('1', 'Low'),
    ('2', 'High'),
    ('3', 'Very High'),
]


class crm_tracking_medium(osv.Model):
    # OLD crm.case.channel
    _name = "crm.tracking.medium"
    _description = "Channels"
    _order = 'name'
    _columns = {
        'name': fields.char('Channel Name', required=True),
        'active': fields.boolean('Active'),
    }
    _defaults = {
        'active': lambda *a: 1,
    }


class crm_tracking_campaign(osv.Model):
    # OLD crm.case.resource.type
    _name = "crm.tracking.campaign"
    _description = "Campaign"
    _rec_name = "name"
    _columns = {
        'name': fields.char('Campaign Name', required=True, translate=True),
        'team_id': fields.many2one('crm.team', 'Sales Team', oldname='section_id'),
    }


class crm_tracking_source(osv.Model):
    _name = "crm.tracking.source"
    _description = "Source"
    _rec_name = "name"
    _columns = {
        'name': fields.char('Source Name', required=True, translate=True),
    }


class crm_tracking_mixin(osv.AbstractModel):
    """Mixin class for objects which can be tracked by marketing. """
    _name = 'crm.tracking.mixin'

    _columns = {
        'campaign_id': fields.many2one('crm.tracking.campaign', 'Campaign',  # old domain ="['|',('team_id','=',team_id),('team_id','=',False)]"
                                       help="This is a name that helps you keep track of your different campaign efforts Ex: Fall_Drive, Christmas_Special"),
        'source_id': fields.many2one('crm.tracking.source', 'Source', help="This is the source of the link Ex: Search Engine, another domain, or name of email list"),
        'medium_id': fields.many2one('crm.tracking.medium', 'Channel', help="This is the method of delivery. Ex: Postcard, Email, or Banner Ad", oldname='channel_id'),
    }

    def tracking_fields(self):
        return [('utm_campaign', 'campaign_id'), ('utm_source', 'source_id'), ('utm_medium', 'medium_id')]

    def tracking_get_values(self, cr, uid, vals, context=None):
        for key, fname in self.tracking_fields():
            field = self._fields[fname]
            value = vals.get(fname) or (request and request.httprequest.cookies.get(key))  # params.get should be always in session by the dispatch from ir_http
            if field.type == 'many2one' and isinstance(value, basestring):
                # if we receive a string for a many2one, we search/create the id
                if value:
                    Model = self.pool[field.comodel_name]
                    rel_id = Model.name_search(cr, uid, value, context=context)
                    if rel_id:
                        rel_id = rel_id[0][0]
                    else:
                        rel_id = Model.create(cr, uid, {'name': value}, context=context)
                vals[fname] = rel_id
            else:
                # Here the code for others cases that many2one
                vals[fname] = value
        return vals

    def _get_default_track(self, cr, uid, field, context=None):
        return self.tracking_get_values(cr, uid, {}, context=context).get(field)

    _defaults = {
        'source_id': lambda self, cr, uid, ctx: self._get_default_track(cr, uid, 'source_id', ctx),
        'campaign_id': lambda self, cr, uid, ctx: self._get_default_track(cr, uid, 'campaign_id', ctx),
        'medium_id': lambda self, cr, uid, ctx: self._get_default_track(cr, uid, 'medium_id', ctx),
    }


class crm_stage(osv.Model):
    """ Model for case stages. This models the main stages of a document
        management flow. Main CRM objects (leads, opportunities, project
        issues, ...) will now use only stages, instead of state and stages.
        Stages are for example used to display the kanban view of records.
    """
    _name = "crm.stage"
    _description = "Stage of case"
    _rec_name = 'name'
    _order = "sequence"

    _columns = {
        'name': fields.char('Stage Name', required=True, translate=True),
        'sequence': fields.integer('Sequence', help="Used to order stages. Lower is better."),
        'probability': fields.float('Probability (%)', required=True, help="This percentage depicts the default/average probability of the Case for this stage to be a success"),
        'on_change': fields.boolean('Change Probability Automatically', help="Setting this stage will change the probability automatically on the opportunity."),
        'requirements': fields.text('Requirements'),
        'team_ids': fields.many2many('crm.team', 'crm_team_stage_rel', 'stage_id', 'team_id', string='Teams',
                        help="Link between stages and sales teams. When set, this limitate the current stage to the selected sales teams."),
        'case_default': fields.boolean('Default to New Sales Team',
                        help="If you check this field, this stage will be proposed by default on each sales team. It will not assign this stage to existing teams."),
        'legend_priority': fields.text(
            'Priority Management Explanation', translate=True,
            help='Explanation text to help users using the star and priority mechanism on stages or issues that are in this stage.'),
        'fold': fields.boolean('Folded in Kanban View',
                               help='This stage is folded in the kanban view when'
                               'there are no records in that stage to display.'),
        'type': fields.selection([('lead', 'Lead'), ('opportunity', 'Opportunity'), ('both', 'Both')],
                                 string='Type', required=True,
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
