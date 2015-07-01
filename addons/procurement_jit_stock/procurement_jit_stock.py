# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2013 Tiny SPRL (<http://tiny.be>).
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

class procurement_order(osv.osv):
    _inherit = "procurement.order"

    def run(self, cr, uid, ids, autocommit=False, context=None):
        context = dict(context or {}, procurement_autorun_defer=True)
        res = super(procurement_order, self).run(cr, uid, ids, autocommit=autocommit, context=context)

        procurement_ids = self.search(cr, uid, [('move_dest_id.procurement_id', 'in', ids)], order='id', context=context)

        if procurement_ids:
            return self.run(cr, uid, procurement_ids, autocommit=autocommit, context=context)
        return res

class stock_move(osv.osv):
    _inherit = "stock.move"

    def _create_procurements(self, cr, uid, moves, context=None):
        res = super(stock_move, self)._create_procurements(cr, uid, moves, context=dict(context or {}, procurement_autorun_defer=True))
        self.pool['procurement.order'].run(cr, uid, res, context=context)
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
