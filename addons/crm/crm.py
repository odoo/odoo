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
    ('0', 'Very Low'),
    ('1', 'Low'),
    ('2', 'Normal'),
    ('3', 'High'),
    ('4', 'Very High'),
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
    
    def _get_default_section_ids(self, cr, uid, context=None):
        """ Gives default section by checking if present in the context """
        section_id = self.pool.get('crm.lead')._resolve_section_id_from_context(cr, uid, context=context) or False
        return section_id and [section_id] or None
    
    _defaults = {
        'sequence': 1,
        'probability': 0.0,
        'on_change': True,
        'fold': False,
        'type': 'both',
        'section_ids': _get_default_section_ids,
        'case_default': lambda self, cr, uid, ctx={}: ctx.get('default_section_id', False) == False,
    }
 
    _sql_constraints = [('stage_name_uniq', 'unique(name)', 'Name should be unique.')] 

    def copy(self, cr, uid, id, default=None, context=None):
        if context is None:
            context = {}
        if default is None:
            default = {}
        default['section_ids'] = []
        section = self.browse(cr, uid, id, context=context)
        if not default.get('name', False):
            default.update(name=_("%s (copy)") % (section.name))
        return super(crm_case_stage, self).copy(cr, uid, id, default, context)
    
    def create(self, cr, uid, vals, context=None):
        if context is None: context = {}
        section_id = context.get('default_section_id')
        type_id = False
        if section_id:
            #check already exist or not
            type_ids = self.search(cr, uid, [('name', '=', vals.get('name'))], context=context, limit=1)
            if type_ids and len(type_ids):
                type_id = type_ids[0]
        if not type_id:
            type_id = super(crm_case_stage, self).create(cr, uid, vals, context=context)
        return type_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:context = {}
        section_id = context.get('default_section_id')
        section_obj = self.pool.get('crm.case.section')
        if section_id:
            context.update({'section_id': section_id})
            if vals.get('name', False):
                for stage in self.browse(cr, uid, ids, context=context):
                    new_stage_id = self.copy(cr, uid, stage.id, default=vals, context=context)
                    section_obj.write(cr, uid, [section_id], {'stage_ids': [(3, stage.id),(4, new_stage_id),]}, context=context)
                    self._update_leads(cr, uid, section_id, stage.id, new_stage_id, context=context)
                return True
        return super(crm_case_stage, self).write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        if context is None: context = {}
        section_id = context.get('default_section_id')
        section_obj = self.pool.get('crm.case.section')
        if not section_id:
            return super(crm_case_stage, self).unlink(cr, uid, ids, context=context)

        for stage in self.browse(cr, uid, ids, context=context):
            section_obj.write(cr, uid, section_id, {'stage_ids': [(3, stage.id)]}, context=context)
            self._update_leads(cr, uid, section_id, stage.id, False, context=context)
        return True

    def _update_leads(self, cr, uid, section_id, old_stage_id, new_stage_id, context=None):
        if context is None: context = {}
        crm_lead_obj = self.pool.get('crm.lead')
        lead_ids = crm_lead_obj.search(cr, uid, [('stage_id', '=', old_stage_id),('section_id', '=', section_id)], context=context)
        return crm_lead_obj.write(cr, uid, lead_ids, {'stage_id': new_stage_id} , context=context)


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
