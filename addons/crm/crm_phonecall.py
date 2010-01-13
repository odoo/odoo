# -*- coding: utf-8 -*-
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

from caldav import common
from dateutil.rrule import *
from osv import fields, osv
import  datetime
import base64
import re
import time
import tools

from tools.translate import _

AVAILABLE_PRIORITIES = [
    ('5','Lowest'),
    ('4','Low'),
    ('3','Normal'),
    ('2','High'),
    ('1','Highest')
]

class crm_phonecall_categ(osv.osv):
    _name = "crm.phonecall.categ"
    _description = "Phonecall Categories"
    _columns = {
            'name': fields.char('Category Name', size=64, required=True),
            'probability': fields.float('Probability (%)', required=True),
            'section_id': fields.many2one('crm.case.section', 'Case Section'),
    }
    _defaults = {
        'probability': lambda *args: 0.0
    }
crm_phonecall_categ()

class crm_phonecall_stage(osv.osv):
    _name = "crm.phonecall.stage"
    _description = "Stage of phonecal case"
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
crm_phonecall_stage()

class crm_phonecall(osv.osv):
    _name = "crm.phonecall"
    _description = "Phonecall Cases"
    _order = "id desc"
    _inherit = 'crm.case'
    _columns = {
        'duration': fields.float('Duration'),
        'categ_id': fields.many2one('crm.phonecall.categ', 'Category', domain="[('section_id','=',section_id)]"),
        'partner_phone': fields.char('Phone', size=32),
        'partner_mobile': fields.char('Mobile', size=32),
        'som': fields.many2one('res.partner.som', 'State of Mind', help="The minds states allow to define a value scale which represents" \
                                                                   "the partner mentality in relation to our services.The scale has" \
                                                                   "to be created with a factor for each level from 0 (Very dissatisfied) to 10 (Extremely satisfied)."),
        'priority': fields.selection(AVAILABLE_PRIORITIES, 'Priority'),
        'canal_id': fields.many2one('res.partner.canal', 'Channel',help="The channels represent the different communication modes available with the customer." \
                                                                " With each commercial opportunity, you can indicate the canall which is this opportunity source."),
        'probability': fields.float('Probability (%)'),
        'planned_revenue': fields.float('Planned Revenue'),
        'date_closed': fields.datetime('Closed', readonly=True),
        'opportunity_id':fields.many2one ('crm.opportunity', 'Opportunity'),        
    }

crm_phonecall()

