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

from openerp.osv import osv
from openerp import SUPERUSER_ID
from openerp.tools.translate import _


class crm_lead(osv.osv):
    _inherit = 'crm.lead'

    def case_interested(self, cr, uid, ids, context=None):
        self.check_access_rights(cr, uid, 'write')
        try:
            stage_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'crm_channel', 'stage_portal_lead_interested')[1]
        except ValueError:
            stage_id = False
        if stage_id:
            self.write(cr, SUPERUSER_ID, ids, {'stage_id': stage_id})
        self.message_post(cr, uid, ids, body=_('I am interested by this lead'), context=context)

    def case_disinterested(self, cr, uid, ids, context=None):
        self.check_access_rights(cr, uid, 'write')
        try:
            stage_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'crm_channel', 'stage_portal_lead_recycle')[1]
        except ValueError:
            stage_id = False
        values = {}
        values = {'partner_assigned_id': False}
        if stage_id:
            values['stage_id'] = stage_id
        self.message_post(cr, uid, ids, body=_('I am not interested by this lead'), context=context)
        self.write(cr, SUPERUSER_ID, ids, values, context=context)
        return {
            'type': 'ir.actions.client',
            'tag': 'next_or_list',
            'params': {
            },
        }
