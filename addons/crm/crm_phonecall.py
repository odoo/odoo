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
        'case_id': fields.many2one ('crm.case', 'Related Case'),
    }

    def msg_new(self, cr, uid, msg):
        mailgate_obj = self.pool.get('mail.gateway')
        msg_body = mailgate_obj.msg_body_get(msg)
        data = {
            'name': msg['Subject'],
            'email_from': msg['From'],
            'email_cc': msg['Cc'],
            'user_id': False,
            'description': msg_body['body'],
            'history_line': [(0, 0, {'description': msg_body['body'], 'email': msg['From'] })],
        }
        res = mailgate_obj.partner_get(cr, uid, msg['From'])
        if res:
            data.update(res)
        res = self.create(cr, uid, data)
        return res

crm_phonecall()


class crm_phonecall_assign_wizard(osv.osv_memory):
    _name = 'crm.phonecall.assign_wizard'

    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Section', required=False),
        'user_id': fields.many2one('res.users', 'Responsible'),
    }

    def _get_default_section(self, cr, uid, context):
        case_id = context.get('active_id',False)
        if not case_id:
            return False
        case_obj = self.pool.get('crm.phonecall')
        case = case_obj.read(cr, uid, case_id, ['state','section_id'])
        if case['state'] in ('done'):
            raise osv.except_osv(_('Error !'), _('You can not assign Closed Case.'))
        return case['section_id']


    _defaults = {
        'section_id': _get_default_section
    }
    def action_create(self, cr, uid, ids, context=None):
        case_obj = self.pool.get('crm.phonecall')
        case_id = context.get('active_id',[])
        res = self.read(cr, uid, ids)[0]
        case = case_obj.browse(cr, uid, case_id)
        if case.state in ('done'):
            raise osv.except_osv(_('Error !'), _('You can not assign Closed Case.'))
        new_case_id = case_obj.copy(cr, uid, case_id, default=
                                            {
                                                'section_id':res.get('section_id',False),
                                                'user_id':res.get('user_id',False),
                                                'case_id' : case.inherit_case_id.id
                                            }, context=context)
        case_obj.case_close(cr, uid, [case_id])
        data_obj = self.pool.get('ir.model.data')
        result = data_obj._get_id(cr, uid, 'crm', 'view_crm_case_phonecalls_filter')
        search_view = data_obj.read(cr, uid, result, ['res_id'])
        value = {
            'name': _('Phone Calls'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'crm.phonecall',
            'res_id': int(new_case_id),
            'type': 'ir.actions.act_window',
            'search_view_id': search_view['res_id']
        }
        return value

crm_phonecall_assign_wizard()
