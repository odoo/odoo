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

from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import SUPERUSER_ID

class procurement_rule(osv.osv):
    _inherit = 'procurement.rule'

    def _get_action(self, cr, uid, context=None):
        return [('manufacture', _('Manufacture'))] + super(procurement_rule, self)._get_action(cr, uid, context=context)


class procurement_order(osv.osv):
    _inherit = 'procurement.order'
    _columns = {
        'bom_id': fields.many2one('mrp.bom', 'BoM', ondelete='cascade', select=True),
        'property_ids': fields.many2many('mrp.property', 'procurement_property_rel', 'procurement_id','property_id', 'Properties'),
        'production_id': fields.many2one('mrp.production', 'Manufacturing Order'),
    }

    def propagate_cancel(self, cr, uid, procurement, context=None):
        if procurement.rule_id.action == 'manufacture' and procurement.production_id:
            self.pool.get('mrp.production').action_cancel(cr, uid, [procurement.production_id.id], context=context)
        return super(procurement_order, self).propagate_cancel(cr, uid, procurement, context=context)

    def _run(self, cr, uid, procurement, context=None):
        if procurement.rule_id and procurement.rule_id.action == 'manufacture':
            #make a manufacturing order for the procurement
            return self.make_mo(cr, uid, [procurement.id], context=context)[procurement.id]
        return super(procurement_order, self)._run(cr, uid, procurement, context=context)

    def _check(self, cr, uid, procurement, context=None):
        if procurement.production_id and procurement.production_id.state == 'done':  # TOCHECK: no better method? 
            return True
        return super(procurement_order, self)._check(cr, uid, procurement, context=context)

    def check_bom_exists(self, cr, uid, ids, context=None):
        """ Finds the bill of material for the product from procurement order.
        @return: True or False
        """
        for procurement in self.browse(cr, uid, ids, context=context):
            properties = [x.id for x in procurement.property_ids]
            bom_id = self.pool.get('mrp.bom')._bom_find(cr, uid, product_id=procurement.product_id.id,
                                                        properties=properties, context=context)
            if not bom_id:
                return False
        return True

    def _get_date_planned(self, cr, uid, procurement, context=None):
        format_date_planned = datetime.strptime(procurement.date_planned,
                                                DEFAULT_SERVER_DATETIME_FORMAT)
        date_planned = format_date_planned - relativedelta(days=procurement.product_id.produce_delay or 0.0)
        date_planned = date_planned - relativedelta(days=procurement.company_id.manufacturing_lead)
        return date_planned

    def _prepare_mo_vals(self, cr, uid, procurement, context=None):
        res_id = procurement.move_dest_id and procurement.move_dest_id.id or False
        newdate = self._get_date_planned(cr, uid, procurement, context=context)
        bom_obj = self.pool.get('mrp.bom')
        if procurement.bom_id:
            bom_id = procurement.bom_id.id
            routing_id = procurement.bom_id.routing_id.id
        else:
            properties = [x.id for x in procurement.property_ids]
            bom_id = bom_obj._bom_find(cr, uid, product_id=procurement.product_id.id,
                                       properties=properties, context=context)
            bom = bom_obj.browse(cr, uid, bom_id, context=context)
            routing_id = bom.routing_id.id
        return {
            'origin': procurement.origin,
            'product_id': procurement.product_id.id,
            'product_qty': procurement.product_qty,
            'product_uom': procurement.product_uom.id,
            'product_uos_qty': procurement.product_uos and procurement.product_uos_qty or False,
            'product_uos': procurement.product_uos and procurement.product_uos.id or False,
            'location_src_id': procurement.location_id.id,
            'location_dest_id': procurement.location_id.id,
            'bom_id': bom_id,
            'routing_id': routing_id,
            'date_planned': newdate.strftime('%Y-%m-%d %H:%M:%S'),
            'move_prod_id': res_id,
            'company_id': procurement.company_id.id,
        }

    def make_mo(self, cr, uid, ids, context=None):
        """ Make Manufacturing(production) order from procurement
        @return: New created Production Orders procurement wise
        """
        res = {}
        production_obj = self.pool.get('mrp.production')
        procurement_obj = self.pool.get('procurement.order')
        for procurement in procurement_obj.browse(cr, uid, ids, context=context):
            if self.check_bom_exists(cr, uid, [procurement.id], context=context):
                #create the MO as SUPERUSER because the current user may not have the rights to do it (mto product launched by a sale for example)
                vals = self._prepare_mo_vals(cr, uid, procurement, context=context)
                produce_id = production_obj.create(cr, SUPERUSER_ID, vals, context=context)
                res[procurement.id] = produce_id
                self.write(cr, uid, [procurement.id], {'production_id': produce_id})
                self.production_order_create_note(cr, uid, procurement, context=context)
                production_obj.action_compute(cr, uid, [produce_id], properties=[x.id for x in procurement.property_ids])
                production_obj.signal_workflow(cr, uid, [produce_id], 'button_confirm')
            else:
                res[procurement.id] = False
                self.message_post(cr, uid, [procurement.id], body=_("No BoM exists for this product!"), context=context)
        return res

    def production_order_create_note(self, cr, uid, procurement, context=None):
        body = _("Manufacturing Order <em>%s</em> created.") % (procurement.production_id.name,)
        self.message_post(cr, uid, [procurement.id], body=body, context=context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
