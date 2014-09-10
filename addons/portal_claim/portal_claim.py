# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
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

from openerp import SUPERUSER_ID
from openerp.addons.base_status.base_stage import base_stage
from openerp.osv import osv


class crm_claim(base_stage, osv.osv):
    _inherit = "crm.claim"

    def default_get(self, cr, uid, fields, context=None):
        res = super(crm_claim, self).default_get(cr, uid, fields, context=context)
        if type(res.get('partner_id')) in (int, long):
            # Special case for portal users, as they are not allowed to call name_get on res.partner
            # We save this call for the web client by returning it in default get
            res['partner_id'] = self.pool['res.partner'].name_get(
                cr, SUPERUSER_ID, [res['partner_id']], context=context)[0]
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
