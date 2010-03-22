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

from osv import fields, osv
import crm
import time

class crm_phonecall(osv.osv):
    _name = "crm.phonecall"
    _description = "Phonecall Cases"
    _order = "id desc"
    _inherit = 'crm.case'
    _columns = {
        'duration': fields.float('Duration'),
        'categ_id': fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.phonecall')]"),
        'partner_phone': fields.char('Phone', size=32),
        'partner_contact': fields.related('partner_address_id', 'name', type="char", string="Contact", size=128),
        'partner_mobile': fields.char('Mobile', size=32),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
        'canal_id': fields.many2one('res.partner.canal', 'Channel',help="The channels represent the different communication modes available with the customer." \
                                                                " With each commercial opportunity, you can indicate the canall which is this opportunity source."),
        'date_closed': fields.datetime('Closed', readonly=True),
        'date': fields.datetime('Date'),
        'opportunity_id':fields.many2one ('crm.opportunity', 'Opportunity'),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'priority': lambda *a: crm.AVAILABLE_PRIORITIES[2][0],
    }
crm_phonecall()

