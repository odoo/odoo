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
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
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
        'campaign_id': fields.many2one('crm.tracking.campaign', 'Campaign',  # old domain ="['|',('section_id','=',section_id),('section_id','=',False)]"
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
        'name': fields.char('Stage Name', required=True, translate=True),
        'sequence': fields.integer('Sequence', help="Used to order stages. Lower is better."),
        'probability': fields.float('Probability (%)', required=True, help="This percentage depicts the default/average probability of the Case for this stage to be a success"),
        'on_change': fields.boolean('Change Probability Automatically', help="Setting this stage will change the probability automatically on the opportunity."),
        'requirements': fields.text('Requirements'),
        'section_ids': fields.many2many('crm.case.section', 'section_stage_rel', 'stage_id', 'section_id', string='Sections',
                                        help="Link between stages and sales teams. When set, this limitate the current stage to the selected sales teams."),
        'default': fields.selection([('none', 'Used in sales team'), ('copy', 'Copy to each new sales team'), ('link', 'Link to each new sales team')], 'Default', help="Will allow you to display the stages (Kanban) as per the option selected:\n"
                    "- Used in sales team: This column will be available in sales team. It will not be linked to new sales team by default.\n" 
                    "- Copy to each new sales team: This column will be duplicated and the copy will be linked to every new sales team.\n"
                    "- Link to each new sales team: The column will be available for all sales team by default.\n"),
        'fold': fields.boolean('Folded in Kanban View',
                               help='This stage is folded in the kanban view when'
                               'there are no records in that stage to display.'),
        'type': fields.selection([('lead', 'Lead'), ('opportunity', 'Opportunity'), ('both', 'Both')],
                                 string='Type', required=True,
                                 help="This field is used to distinguish stages related to Leads from stages related to Opportunities, or to specify stages available for both types."),
    }

    def _get_default_section_id(self, cr, uid, context=None):
        section_id = self.pool['crm.lead']._resolve_section_id_from_context(cr, uid, context=context)
        if section_id:
            return [section_id]
        return None

    _defaults = {
        'sequence': 1,
        'probability': 0.0,
        'on_change': True,
        'fold': False,
        'type': 'both',
        'default': 'copy',
        'section_ids': _get_default_section_id
    }

    def create(self, cr, uid, vals, context=None):
        if context is None: context = {}
        section_id = self._get_default_section_id(cr, uid, context=context)
        if vals.get('default') == 'copy' and section_id:
            vals.update({'section_ids': False})
            type_id = super(crm_case_stage, self).create(cr, uid, vals, context=context)
            context.update({'default_section_id': False})
            type_id = self.copy(cr, uid, type_id, default={'default': 'none', 'section_ids': [[6, False, section_id]]}, context=context)
        else:
            type_id = super(crm_case_stage, self).create(cr, uid, vals, context=context)
        return type_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None: context = {}
        section_id = self._get_default_section_id(cr, uid, context=context)
        section_obj = self.pool.get('crm.case.section')
        if vals.get('default') == 'copy' and section_id:
            for stage in self.browse(cr, uid, ids, context=context):
                new_stage_id = self.copy(cr, uid, stage.id, vals, context=context)
                section_obj.write(cr, uid, section_id, {'stage_ids': [(3, stage.id),(4, new_stage_id),]}, context=context)
                self._update_leads(cr, uid, section_id, stage.id, new_stage_id, context=context)
                return True
        elif vals.get('default') == 'copy':
            for stage in self.browse(cr, uid, ids, context=context):
                values = vals.copy()
                if stage.section_ids:
                    self.copy(cr, uid, stage.id, values, context=context)
                    values.update({'default': 'none'})
                super(crm_case_stage, self).write(cr, uid, stage.id, values, context=context)
            return True
        return super(crm_case_stage, self).write(cr, uid, ids, vals, context=context)

    def _update_leads(self, cr, uid, section_id, old_stage_id, new_stage_id, context=None):
        if context is None: context = {}
        crm_lead_obj = self.pool.get('crm.lead')
        lead_ids = crm_lead_obj.search(cr, uid, [('stage_id', '=', old_stage_id),('section_id', 'in', section_id)], context=context)
        return crm_lead_obj.write(cr, uid, lead_ids, {'stage_id': new_stage_id}, context=context)


class crm_case_categ(osv.osv):
    """ Category of Case """
    _name = "crm.case.categ"
    _description = "Category of Case"
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'object_id': fields.many2one('ir.model', 'Object Name'),
    }

    def _find_object_id(self, cr, uid, context=None):
        """Finds id for case object"""
        context = context or {}
        object_id = context.get('object_id', False)
        ids = self.pool.get('ir.model').search(cr, uid, ['|', ('id', '=', object_id), ('model', '=', context.get('object_name', False))])
        return ids and ids[0] or False
    _defaults = {
        'object_id': _find_object_id
    }


class crm_payment_mode(osv.osv):
    """ Payment Mode for Fund """
    _name = "crm.payment.mode"
    _description = "CRM Payment Mode"
    _columns = {
        'name': fields.char('Name', required=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
