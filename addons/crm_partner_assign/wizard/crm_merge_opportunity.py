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
from osv import osv, fields
from tools.translate import _


class crm_merge_opportunity_assign_partner(osv.osv_memory):
    """Merge two Opportunities"""

    _inherit = 'crm.merge.opportunity'
    
    def _update_data(self, op_ids, oldest_opp):
		data = super(crm_merge_opportunity_assign_partner, self)._update_data(op_ids, oldest_opp)
			
		new_data = {
			'partner_latitude': self._get_first_not_null('partner_latitude', op_ids, oldest_opp),
			'partner_longitude': self._get_first_not_null('partner_longitude', op_ids, oldest_opp),
			'partner_assigned_id': self._get_first_not_null_id('partner_assigned_id', op_ids, oldest_opp), 
			'date_assign' : self._get_first_not_null('date_assign', op_ids, oldest_opp),
		}
		data.update(new_data)
		return data

crm_merge_opportunity_assign_partner()
