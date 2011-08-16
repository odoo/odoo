#-*- coding: utf-8 -*-
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

from osv import fields, osv
from tools.translate import _
import crm


AVAILABLE_STATES = [
    ('draft','Draft'),
    ('open','Open'),
    ('cancel', 'Lost'),
    ('done', 'Converted'),
    ('pending','Pending')
]

class crm_opportunity(osv.osv):
    """ Opportunity Cases """
    _order = "priority,date_action,id desc"
    _inherit = 'crm.lead'
    _columns = {
        # From crm.case
        'partner_address_id': fields.many2one('res.partner.address', 'Partner Contact', \
                                 domain="[('partner_id','=',partner_id)]"), 

        # Opportunity fields
        'probability': fields.float('Probability (%)',group_operator="avg"),
        'planned_revenue': fields.float('Expected Revenue'),
        'ref': fields.reference('Reference', selection=crm._links_get, size=128),
        'ref2': fields.reference('Reference 2', selection=crm._links_get, size=128),
        'phone': fields.char("Phone", size=64),
        'date_deadline': fields.date('Expected Closing'),
        'date_action': fields.date('Next Action Date'),
        'title_action': fields.char('Next Action', size=64),
        'stage_id': fields.many2one('crm.case.stage', 'Stage', domain="[(section_ids', '=', section_id)]"),
     }
    
    def _case_close_generic(self, cr, uid, ids, find_stage, *args):
        res = super(crm_opportunity, self).case_close(cr, uid, ids, *args)
        for case in self.browse(cr, uid, ids):
            #if the case is not an opportunity close won't change the stage
            if not case.type == 'opportunity':
                return res
                
            value = {}
            stage_id = find_stage(cr, uid, 'opportunity', case.section_id.id or False)
            if stage_id:
                stage_obj = self.pool.get('crm.case.stage').browse(cr, uid, stage_id)
                value.update({'stage_id': stage_id})
                if stage_obj.on_change:
                    value.update({'probability': stage_obj.probability})
                
            #Done un crm.case
            #value.update({'date_closed': time.strftime('%Y-%m-%d %H:%M:%S')})
            

            self.write(cr, uid, ids, value)
        return res
    
    def case_close(self, cr, uid, ids, *args):
        """Overrides close for crm_case for setting probability and close date
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case Ids
        @param *args: Tuple Value for additional Params
        """
        res = self._case_close_generic(cr, uid, ids, self._find_won_stage, *args)
        
        for (id, name) in self.name_get(cr, uid, ids):
            opp = self.browse(cr, uid, id)
            if opp.type == 'opportunity':
                message = _("The opportunity '%s' has been won.") % name
                self.log(cr, uid, id, message)
        return res

    def case_mark_lost(self, cr, uid, ids, *args):
        """Mark the case as lost: state = done and probability = 0%
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case Ids
        @param *args: Tuple Value for additional Params
        """
        res = self._case_close_generic(cr, uid, ids, self._find_lost_stage, *args)
        
        for (id, name) in self.name_get(cr, uid, ids):
            opp = self.browse(cr, uid, id)
            if opp.type == 'opportunity':
                message = _("The opportunity '%s' has been marked as lost.") % name
                self.log(cr, uid, id, message)
        return res
    
    def case_cancel(self, cr, uid, ids, *args):
        """Overrides cancel for crm_case for setting probability
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case Ids
        @param *args: Tuple Value for additional Params
        """
        res = super(crm_opportunity, self).case_cancel(cr, uid, ids, args)
        self.write(cr, uid, ids, {'probability' : 0.0})
        return res

    def case_reset(self, cr, uid, ids, *args):
        """Overrides reset as draft in order to set the stage field as empty
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case Ids
        @param *args: Tuple Value for additional Params
        """
        res = super(crm_opportunity, self).case_reset(cr, uid, ids, *args)
        self.write(cr, uid, ids, {'stage_id': False, 'probability': 0.0})
        return res
   
 
    def case_open(self, cr, uid, ids, *args):
        """Overrides open for crm_case for setting Open Date
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case's Ids
        @param *args: Give Tuple Value
        """
        res = super(crm_opportunity, self).case_open(cr, uid, ids, *args)
        
        return res

    def onchange_stage_id(self, cr, uid, ids, stage_id, context=None):

        """ @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of stage’s IDs
            @stage_id: change state id on run time """
        if not stage_id:
            return {'value':{}}
        
        stage = self.pool.get('crm.case.stage').browse(cr, uid, stage_id, context=context)

        if not stage.on_change:
            return {'value':{}}
        return {'value':{'probability': stage.probability}}

    _defaults = {
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.lead', context=c),
        'priority': crm.AVAILABLE_PRIORITIES[2][0],
    }

    def action_makeMeeting(self, cr, uid, ids, context=None):
        """
        This opens Meeting's calendar view to schedule meeting on current Opportunity
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Opportunity to Meeting IDs
        @param context: A standard dictionary for contextual values

        @return : Dictionary value for created Meeting view
        """
        value = {}
        for opp in self.browse(cr, uid, ids, context=context):
            data_obj = self.pool.get('ir.model.data')

            # Get meeting views
            result = data_obj._get_id(cr, uid, 'crm', 'view_crm_case_meetings_filter')
            res = data_obj.read(cr, uid, result, ['res_id'])
            id1 = data_obj._get_id(cr, uid, 'crm', 'crm_case_calendar_view_meet')
            id2 = data_obj._get_id(cr, uid, 'crm', 'crm_case_form_view_meet')
            id3 = data_obj._get_id(cr, uid, 'crm', 'crm_case_tree_view_meet')
            if id1:
                id1 = data_obj.browse(cr, uid, id1, context=context).res_id
            if id2:
                id2 = data_obj.browse(cr, uid, id2, context=context).res_id
            if id3:
                id3 = data_obj.browse(cr, uid, id3, context=context).res_id

            context = {
                'default_opportunity_id': opp.id,
                'default_partner_id': opp.partner_id and opp.partner_id.id or False,
                'default_user_id': uid, 
                'default_section_id': opp.section_id and opp.section_id.id or False,
                'default_email_from': opp.email_from,
                'default_state': 'open',  
                'default_name': opp.name
            }
            value = {
                'name': _('Meetings'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'calendar,form,tree',
                'res_model': 'crm.meeting',
                'view_id': False,
                'views': [(id1, 'calendar'), (id2, 'form'), (id3, 'tree')],
                'type': 'ir.actions.act_window',
                'search_view_id': res['res_id'],
                'nodestroy': True
            }
        return value

crm_opportunity()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
