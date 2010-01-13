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

class crm_helpdesk_categ(osv.osv):
    _name = "crm.helpdesk.categ"
    _description = "Helpdesk Categories"
    _columns = {
            'name': fields.char('Category Name', size=64, required=True),
            'probability': fields.float('Probability (%)', required=True),
            'section_id': fields.many2one('crm.case.section', 'Case Section'),
    }
    _defaults = {
        'probability': lambda *args: 0.0
    }
crm_helpdesk_categ()

class crm_helpdesk(osv.osv):
    _name = "crm.helpdesk"
    _description = "Helpdesk Cases"
    _order = "id desc"
    _inherit = 'crm.case'
    _columns = {
            'date_closed': fields.datetime('Closed', readonly=True),
            'ref' : fields.reference('Reference', selection=_links_get, size=128),
            'ref2' : fields.reference('Reference 2', selection=_links_get, size=128),
            'canal_id': fields.many2one('res.partner.canal', 'Channel',help="The channels represent the different communication modes available with the customer." \
                                                                            " With each commercial opportunity, you can indicate the canall which is this opportunity source."),
            'planned_revenue': fields.float('Planned Revenue'),
            'planned_cost': fields.float('Planned Costs'),
            'priority': fields.selection(AVAILABLE_PRIORITIES, 'Priority'),
            'probability': fields.float('Probability (%)'),
            'som': fields.many2one('res.partner.som', 'State of Mind', help="The minds states allow to define a value scale which represents" \
                                                                   "the partner mentality in relation to our services.The scale has" \
                                                                   "to be created with a factor for each level from 0 (Very dissatisfied) to 10 (Extremely satisfied)."),
            'categ_id': fields.many2one('crm.helpdesk.categ', 'Category', domain="[('section_id','=',section_id)]"),
            'duration': fields.float('Duration'),
    }
    
crm_helpdesk()



