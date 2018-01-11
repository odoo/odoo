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
from openerp.osv import fields, osv
from openerp.tools.translate import _

class stock_picking_to_wave(osv.osv_memory):
    _name = 'stock.picking.to.wave'
    _description = 'Add pickings to a picking wave'
    _columns = {
        'wave_id': fields.many2one('stock.picking.wave', 'Picking Wave', required=True),
    }

    def attach_pickings(self, cr, uid, ids, context=None):
        #use active_ids to add picking line to the selected wave
        wave_id = self.browse(cr, uid, ids, context=context)[0].wave_id.id
        picking_ids = context.get('active_ids', False)
        return self.pool.get('stock.picking').write(cr, uid, picking_ids, {'wave_id': wave_id})