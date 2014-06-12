# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.odoo.com>
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
from openerp.osv import fields, osv


class stock_warehouse(osv.osv):
    _inherit = "stock.warehouse"
    _columns = {
        'region_id': fields.many2one('l10n_be_intrastat_declaration.regions', 'Intratstat region'),
    }

    def get_regionid_from_locationid(self, cr, uid, locationid, context=None):
        location_mod = self.pool['stock.location']

        location_id = locationid
        toret = None
        stopsearching = False

        while not stopsearching:
            warehouse_ids = self.search(cr, uid, [('lot_stock_id','=',location_id)])
            if warehouse_ids and warehouse_ids[0]:
                stopsearching = True
                toret = self.browse(cr, uid, warehouse_ids[0]).region_id.id
            else:
                loc = location_mod.browse(cr, uid, location_id)
                if loc and loc.location_id:
                    location_id = loc.location_id
                else:
                    #no more parent
                    stopsearching = True

        return toret
