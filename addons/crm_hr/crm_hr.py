# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import crm

class crm_job_categ(osv.osv):
    _name = "crm.job.categ"
    _description = "Job Categories"
    _columns = {
            'name': fields.char('Category Name', size=64, required=True),
            'probability': fields.float('Probability (%)', required=True),
            'section_id': fields.many2one('crm.case.section', 'Case Section'),
    }
    _defaults = {
        'probability': lambda *args: 0.0
    }
crm_job_categ()

class crm_job_type(osv.osv):
    _name = "crm.job.type"
    _description = "Job Type"
    _rec_name = "name"
    _columns = {
        'name': fields.char('Claim Type Name', size=64, required=True, translate=True),
        'section_id': fields.many2one('crm.case.section', 'Case Section'),
    }
crm_job_type()

class crm_job_stage(osv.osv):
    _name = "crm.job.stage"
    _description = "Stage of job case"
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
crm_job_stage()

class crm_job(osv.osv):
    _name = "crm.job"
    _description = "Job Cases"
    _order = "id desc"
    _inherit ='crm.case'    
    _columns = {        
            'date_closed': fields.datetime('Closed', readonly=True),
            'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),            
            'categ_id': fields.many2one('crm.job.categ', 'Category', domain="[('section_id','=',section_id)]"),
            'planned_revenue': fields.float('Planned Revenue'),
            'planned_cost': fields.float('Planned Costs'),
            'probability': fields.float('Probability (%)'),     
            'partner_name': fields.char("Employee's Name", size=64),
            'partner_name2': fields.char('Employee Email', size=64),
            'partner_phone': fields.char('Phone', size=32),
            'partner_mobile': fields.char('Mobile', size=32), 
            'stage_id': fields.many2one ('crm.job.stage', 'Stage', domain="[('section_id','=',section_id)]"),
            'type_id': fields.many2one('crm.job.type', 'Type Name', domain="[('section_id','=',section_id)]"),
            'duration': fields.float('Duration'),
            'case_id': fields.many2one('crm.case', 'Related Case'),
            'ref' : fields.reference('Reference', selection=crm._links_get, size=128),
            'ref2' : fields.reference('Reference 2', selection=crm._links_get, size=128),
            'canal_id': fields.many2one('res.partner.canal', 'Channel',help="The channels represent the different communication modes available with the customer." \
                                                                        " With each commercial opportunity, you can indicate the canall which is this opportunity source."),
            'som': fields.many2one('res.partner.som', 'State of Mind', help="The minds states allow to define a value scale which represents" \
                                                                       "the partner mentality in relation to our services.The scale has" \
                                                                       "to be created with a factor for each level from 0 (Very dissatisfied) to 10 (Extremely satisfied)."),

            
    }
    def onchange_categ_id(self, cr, uid, ids, categ, context={}):
        if not categ:
            return {'value':{}}
        cat = self.pool.get('crm.categ.categ').browse(cr, uid, categ, context).probability
        return {'value':{'probability':cat}}
   
crm_job()
