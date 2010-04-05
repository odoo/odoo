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

from osv import fields,osv,orm
import crm

AVAILABLE_STATES = [
    ('draft','New'),
    ('open','Open'),
    ('cancel', 'Lost'),
    ('done', 'Converted'),
    ('pending','Pending')
]

class crm_opportunity(osv.osv):
    _name = "crm.opportunity"
    _description = "Opportunity Cases"
    _order = "id desc"
    _inherit = 'crm.case'
    _columns = {
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.opportunity')]"),
        'categ_id': fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.opportunity')]"),
        'type_id': fields.many2one('crm.case.resource.type', 'Resource Type', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.opportunity')]"),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
        'probability': fields.float('Probability (%)'),
        'planned_revenue': fields.float('Expected Revenue'),
        'ref' : fields.reference('Reference', selection=crm._links_get, size=128),
        'ref2' : fields.reference('Reference 2', selection=crm._links_get, size=128),
        'date_closed': fields.datetime('Closed', readonly=True),
        'user_id': fields.many2one('res.users', 'Salesman'),
        'phone': fields.char("Phone", size=64),
        'date_deadline': fields.date('Expected Closing'),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True,
                                  help='The state is set to \'Draft\', when a case is created.\
                                  \nIf the case is in progress the state is set to \'Open\'.\
                                  \nWhen the case is over, the state is set to \'Done\'.\
                                  \nIf the case needs to be reviewed then the state is set to \'Pending\'.'),
    }
    def onchange_stage_id(self, cr, uid, ids, stage_id, context={}):
        if not stage_id:
            return {'value':{}}
        stage = self.pool.get('crm.case.stage').browse(cr, uid, stage_id, context)
        if not stage.on_change:
            return {'value':{}}
        return {'value':{'probability':stage.probability}}

    def stage_next(self, cr, uid, ids, context={}):
        res = super(crm_opportunity, self).stage_next(cr, uid, ids, context=context)
        for case in self.browse(cr, uid, ids, context):
            if case.stage_id and case.stage_id.on_change:                                
                self.write(cr, uid, [case.id], {'probability': case.stage_id.probability})
        return res

    def stage_previous(self, cr, uid, ids, context={}):
        res = super(crm_opportunity, self).stage_previous(cr, uid, ids, context=context)
        for case in self.browse(cr, uid, ids, context):
            if case.stage_id and case.stage_id.on_change:                                
                self.write(cr, uid, [case.id], {'probability': case.stage_id.probability})
        return res 

    _defaults = {
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.opportunity', context=c),
    }

crm_opportunity()

