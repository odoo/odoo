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

import time
import re
import os

import mx.DateTime
import base64

from tools.translate import _

import tools
from osv import fields,osv,orm
from osv.orm import except_orm

AVAILABLE_PRIORITIES = [
    ('5','Lowest'),
    ('4','Low'),
    ('3','Normal'),
    ('2','High'),
    ('1','Highest')
]

def _links_get(self, cr, uid, context={}):
    obj = self.pool.get('res.request.link')
    ids = obj.search(cr, uid, [])
    res = obj.read(cr, uid, ids, ['object', 'name'], context)
    return [(r['object'], r['name']) for r in res]

class crm_opportunity_categ(osv.osv):
    _name = "crm.opportunity.categ"
    _description = "Opportunity Categories"
    _columns = {
            'name': fields.char('Category Name', size=64, required=True),
            'probability': fields.float('Probability (%)', required=True),
            'section_id': fields.many2one('crm.case.section', 'Case Section'),
    }
    _defaults = {
        'probability': lambda *args: 0.0
    }
crm_opportunity_categ()

class crm_opportunity_type(osv.osv):
    _name = "crm.opportunity.type"
    _description = "Opportunity Type"
    _rec_name = "name"
    _columns = {
        'name': fields.char('lead Type Name', size=64, required=True, translate=True),
        'section_id': fields.many2one('crm.case.section', 'Case Section'),
    }
crm_opportunity_type()

class crm_opportunity_stage(osv.osv):
    _name = "crm.opportunity.stage"
    _description = "Stage of opportunity case"
    _rec_name = 'name'
    _order = "sequence"
    _columns = {
        'name': fields.char('Stage Name', size=64, required=True, translate=True),
        'section_id': fields.many2one('crm.case.section', 'Case Section'),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of case stages."),
    }
    _defaults = {
        'sequence': lambda *args: 1
    }
crm_opportunity_stage()

class crm_opportunity(osv.osv):
    _name = "crm.opportunity"
    _description = "Opportunity Cases"
    _order = "id desc"
    _inherit = 'crm.case'  
    _columns = {        
        'stage_id': fields.many2one ('crm.opportunity.stage', 'Stage', domain="[('section_id','=',section_id)]"),
        'categ_id': fields.many2one('crm.opportunity.categ', 'Category', domain="[('section_id','=',section_id)]"),
        'type_id': fields.many2one('crm.opportunity.type', 'Opportunity Type', domain="[('section_id','=',section_id)]"),
        'priority': fields.selection(AVAILABLE_PRIORITIES, 'Priority'),
        'probability': fields.float('Probability (%)'),
        'planned_revenue': fields.float('Planned Revenue'),
        'planned_cost': fields.float('Planned Costs'),
        'canal_id': fields.many2one('res.partner.canal', 'Channel',help="The channels represent the different communication modes available with the customer." \
                                                                        " With each commercial opportunity, you can indicate the canall which is this opportunity source."),
        'som': fields.many2one('res.partner.som', 'State of Mind', help="The minds states allow to define a value scale which represents" \
                                                                   "the partner mentality in relation to our services.The scale has" \
                                                                   "to be created with a factor for each level from 0 (Very dissatisfied) to 10 (Extremely satisfied)."),
        'ref' : fields.reference('Reference', selection=_links_get, size=128),
        'ref2' : fields.reference('Reference 2', selection=_links_get, size=128),
        'date_closed': fields.datetime('Closed', readonly=True),
        'phonecall_id':fields.many2one ('crm.phonecall', 'Phonecall'),
    }
crm_opportunity()

