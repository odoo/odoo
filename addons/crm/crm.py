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

from openerp import models, fields, api
from openerp.http import request

AVAILABLE_PRIORITIES = [
    ('0', 'Normal'),
    ('1', 'Low'),
    ('2', 'High'),
    ('3', 'Very High'),
]


class crm_tracking_medium(models.Model):
    # OLD crm.case.channel
    _name = "crm.tracking.medium"
    _description = "Channels"
    _order = 'name'

    name = fields.Char('Channel Name', required=True)
    active = fields.Boolean('Active', default=lambda *a: 1)

class crm_tracking_campaign(models.Model):
    # OLD crm.case.resource.type
    _name = "crm.tracking.campaign"
    _description = "Campaign"
    _rec_name = "name"
    
    name = fields.Char('Campaign Name', required=True, translate=True)
    team_id = fields.Many2one('crm.team', 'Sales Team')
    
class crm_tracking_source(models.Model):
    _name = "crm.tracking.source"
    _description = "Source"
    _rec_name = "name"

    name = fields.Char('Source Name', required=True, translate=True)

class crm_stage(models.Model):
    """ Model for case stages. This models the main stages of a document
        management flow. Main CRM objects (leads, opportunities, project
        issues, ...) will now use only stages, instead of state and stages.
        Stages are for example used to display the kanban view of records.
    """
    _name = "crm.stage"
    _description = "Stage of case"
    _rec_name = 'name'
    _order = "sequence"

    name = fields.Char('Stage Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', help="Used to order stages. Lower is better.")
    probability = fields.Float('Probability (%)', required=True, help="This percentage depicts the default/average probability of the Case for this stage to be a success",
        default=0.0)
    on_change = fields.Boolean('Change Probability Automatically', help="Setting this stage will change the probability automatically on the opportunity.",
        default=True)
    requirements = fields.Text('Requirements')
    team_ids = fields.Many2many('crm.team', 'crm_team_stage_rel', 'stage_id', 'team_id', 
        string='teams',
        help="Link between stages and sales teams. When set, this limitate the current stage to the selected sales teams.")
    case_default = fields.Boolean('Default to New Sales Team',
        help="If you check this field, this stage will be proposed by default on each sales team. It will not assign this stage to existing teams.",
        default=True)
    fold = fields.Boolean('Folded in Kanban View',
        help='This stage is folded in the kanban view when'
        'there are no records in that stage to display.',
        default=False)
    type = fields.Selection([('lead', 'Lead'), ('opportunity', 'Opportunity'), ('both', 'Both')],
        string='Type', required=True,
        help="This field is used to distinguish stages related to Leads from stages related to Opportunities, or to specify stages available for both types.",
        default='both')

from openerp.osv import osv, fields
class crm_tracking_mixin(osv.AbstractModel):
    """Mixin class for objects which can be tracked by marketing. """
    _name = 'crm.tracking.mixin'

    _columns = {
        'campaign_id': fields.many2one('crm.tracking.campaign', 'Campaign',  # old domain ="['|',('team_id','=',team_id),('team_id','=',False)]"
                                       help="This is a name that helps you keep track of your different campaign efforts Ex: Fall_Drive, Christmas_Special"),
        'source_id': fields.many2one('crm.tracking.source', 'Source', help="This is the source of the link Ex: Search Engine, another domain, or name of email list"),
        'medium_id': fields.many2one('crm.tracking.medium', 'Channel', help="This is the method of delivery. Ex: Postcard, Email, or Banner Ad"),
    }

    def tracking_fields(self):
        return [('utm_campaign', 'campaign_id'), ('utm_source', 'source_id'), ('utm_medium', 'medium_id')]

    def tracking_get_values(self, cr, uid, vals, context=None):
        for key, field in self.tracking_fields():
            column = self._all_columns[field].column
            value = vals.get(field) or (request and request.httprequest.cookies.get(key))  # params.get should be always in session by the dispatch from ir_http
            if column._type in ['many2one'] and isinstance(value, basestring):  # if we receive a string for a many2one, we search / create the id
                if value:
                    Model = self.pool[column._obj]
                    rel_id = Model.name_search(cr, uid, value, context=context)
                    if rel_id:
                        rel_id = rel_id[0][0]
                    else:
                        rel_id = Model.create(cr, uid, {'name': value}, context=context)
                vals[field] = rel_id
            # Here the code for others cases that many2one
            else:
                vals[field] = value
        return vals

    def _get_default_track(self, cr, uid, field, context=None):
        return self.tracking_get_values(cr, uid, {}, context=context).get(field)

    _defaults = {
        'source_id': lambda self, cr, uid, ctx: self._get_default_track(cr, uid, 'source_id', ctx),
        'campaign_id': lambda self, cr, uid, ctx: self._get_default_track(cr, uid, 'campaign_id', ctx),
        'medium_id': lambda self, cr, uid, ctx: self._get_default_track(cr, uid, 'medium_id', ctx),
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
