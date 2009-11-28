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

from mx import DateTime
import time
import netsvc
from osv import fields, osv
from tools import config
from tools.translate import _
import tools


#----------------------------------------------------------
# Incoterms
#----------------------------------------------------------
class stock_incoterms(osv.osv):
    _name = "stock.incoterms"
    _description = "Incoterms"
    _columns = {
        'name': fields.char('Name', size=64, required=True,help="Incoterms are series of sales terms.They are used to divide transaction costs and responsibilities between buyer and seller and reflect state-of-the-art transportation practices."),
        'code': fields.char('Code', size=3, required=True,help="code for Incoterms"),
        'active': fields.boolean('Active'),
    }
    _defaults = {
        'active': lambda *a: True,
    }

stock_incoterms()


#----------------------------------------------------------
# Stock Location
#----------------------------------------------------------
class stock_location(osv.osv):
    _name = "stock.location"
    _description = "Location"
    _parent_name = "location_id"
    _parent_store = True
    _parent_order = 'id'
    _order = 'parent_left'

    def name_get(self, cr, uid, ids, context={}):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['name','location_id'], context)
        res = []
        for record in reads:
            name = record['name']
            if context.get('full',False):
                if record['location_id']:
                    name = record['location_id'][1]+' / '+name
                res.append((record['id'], name))
            else:
                res.append((record['id'], name))
        return res

    def _complete_name(self, cr, uid, ids, name, args, context):
        def _get_one_full_name(location, level=4):
            if location.location_id:
                parent_path = _get_one_full_name(location.location_id, level-1) + "/"
            else:
                parent_path = ''
            return parent_path + location.name
        res = {}
        for m in self.browse(cr, uid, ids, context=context):
            res[m.id] = _get_one_full_name(m)
        return res

    def _product_qty_available(self, cr, uid, ids, field_names, arg, context={}):
        res = {}
        for id in ids:
            res[id] = {}.fromkeys(field_names, 0.0)
        if ('product_id' not in context) or not ids:
            return res
        #location_ids = self.search(cr, uid, [('location_id', 'child_of', ids)])
        for loc in ids:
            context['location'] = [loc]
            prod = self.pool.get('product.product').browse(cr, uid, context['product_id'], context)
            if 'stock_real' in field_names:
                res[loc]['stock_real'] = prod.qty_available
            if 'stock_virtual' in field_names:
                res[loc]['stock_virtual'] = prod.virtual_available
        return res

    def product_detail(self, cr, uid, id, field, context={}):
        res = {}
        res[id] = {}
        final_value = 0.0
        field_to_read = 'virtual_available'
        if field == 'stock_real_value':
            field_to_read = 'qty_available'
        cr.execute('select distinct product_id from stock_move where (location_id=%s) or (location_dest_id=%s)', (id, id))
        result = cr.dictfetchall()
        if result:
            for r in result:
                c = (context or {}).copy()
                c['location'] = id
                product = self.pool.get('product.product').read(cr, uid, r['product_id'], [field_to_read, 'standard_price'], context=c)
                final_value += (product[field_to_read] * product['standard_price'])
        return final_value

    def _product_value(self, cr, uid, ids, field_names, arg, context={}):
        result = {}
        for id in ids:
            result[id] = {}.fromkeys(field_names, 0.0)
        for field_name in field_names:
            for loc in ids:
                ret_dict = self.product_detail(cr, uid, loc, field=field_name)
                result[loc][field_name] = ret_dict
        return result

    _columns = {
        'name': fields.char('Location Name', size=64, required=True, translate=True),
        'active': fields.boolean('Active'),
        'company_id': fields.many2one('res.company','Company',required=True),
        'usage': fields.selection([('supplier', 'Supplier Location'), ('view', 'View'), ('internal', 'Internal Location'), ('customer', 'Customer Location'), ('inventory', 'Inventory'), ('procurement', 'Procurement'), ('production', 'Production')], 'Location Type', required=True),
        'allocation_method': fields.selection([('fifo', 'FIFO'), ('lifo', 'LIFO'), ('nearest', 'Nearest')], 'Allocation Method', required=True),

        'complete_name': fields.function(_complete_name, method=True, type='char', size=100, string="Location Name"),

        'stock_real': fields.function(_product_qty_available, method=True, type='float', string='Real Stock', multi="stock"),
        'stock_virtual': fields.function(_product_qty_available, method=True, type='float', string='Virtual Stock', multi="stock"),

        'account_id': fields.many2one('account.account', string='Inventory Account', domain=[('type', '!=', 'view')]),
        'location_id': fields.many2one('stock.location', 'Parent Location', select=True, ondelete='cascade'),
        'child_ids': fields.one2many('stock.location', 'location_id', 'Contains'),

        'chained_location_id': fields.many2one('stock.location', 'Chained Location If Fixed'),
        'chained_location_type': fields.selection([('none', 'None'), ('customer', 'Customer'), ('fixed', 'Fixed Location')],
            'Chained Location Type', required=True),
        'chained_auto_packing': fields.selection(
            [('auto', 'Automatic Move'), ('manual', 'Manual Operation'), ('transparent', 'Automatic No Step Added')],
            'Automatic Move',
            required=True,
            help="This is used only if you selected a chained location type.\n" \
                "The 'Automatic Move' value will create a stock move after the current one that will be "\
                "validated automatically. With 'Manual Operation', the stock move has to be validated "\
                "by a worker. With 'Automatic No Step Added', the location is replaced in the original move."
            ),
        'chained_delay': fields.integer('Chained Delay (days)'),
        'address_id': fields.many2one('res.partner.address', 'Location Address'),
        'icon': fields.selection(tools.icons, 'Icon', size=64),

        'comment': fields.text('Additional Information'),
        'posx': fields.integer('Corridor (X)'),
        'posy': fields.integer('Shelves (Y)'),
        'posz': fields.integer('Height (Z)'),

        'parent_left': fields.integer('Left Parent', select=1),
        'parent_right': fields.integer('Right Parent', select=1),
        'stock_real_value': fields.function(_product_value, method=True, type='float', string='Real Stock Value', multi="stock"),
        'stock_virtual_value': fields.function(_product_value, method=True, type='float', string='Virtual Stock Value', multi="stock"),
    }
    _defaults = {
        'active': lambda *a: 1,
        'usage': lambda *a: 'internal',
        'allocation_method': lambda *a: 'fifo',
        'chained_location_type': lambda *a: 'none',
        'chained_auto_packing': lambda *a: 'manual',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.location', c)
        'posx': lambda *a: 0,
        'posy': lambda *a: 0,
        'posz': lambda *a: 0,
        'icon': lambda *a: False
    }

    def chained_location_get(self, cr, uid, location, partner=None, product=None, context={}):
        result = None
        if location.chained_location_type == 'customer':
            if partner:
                result = partner.property_stock_customer
        elif location.chained_location_type == 'fixed':
            result = location.chained_location_id
        if result:
            return result, location.chained_auto_packing, location.chained_delay
        return result

    def picking_type_get(self, cr, uid, from_location, to_location, context={}):
        result = 'internal'
        if (from_location.usage=='internal') and (to_location and to_location.usage in ('customer', 'supplier')):
            result = 'delivery'
        elif (from_location.usage in ('supplier', 'customer')) and (to_location.usage=='internal'):
            result = 'in'
        return result

    def _product_get_all_report(self, cr, uid, ids, product_ids=False,
            context=None):
        return self._product_get_report(cr, uid, ids, product_ids, context,
                recursive=True)

    def _product_get_report(self, cr, uid, ids, product_ids=False,
            context=None, recursive=False):
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product')
        if not product_ids:
            product_ids = product_obj.search(cr, uid, [])

        products = product_obj.browse(cr, uid, product_ids, context=context)
        products_by_uom = {}
        products_by_id = {}
        for product in products:
            products_by_uom.setdefault(product.uom_id.id, [])
            products_by_uom[product.uom_id.id].append(product)
            products_by_id.setdefault(product.id, [])
            products_by_id[product.id] = product

        result = {}
        result['product'] = []
        for id in ids:
            quantity_total = 0.0
            total_price = 0.0
            for uom_id in products_by_uom.keys():
                fnc = self._product_get
                if recursive:
                    fnc = self._product_all_get
                ctx = context.copy()
                ctx['uom'] = uom_id
                qty = fnc(cr, uid, id, [x.id for x in products_by_uom[uom_id]],
                        context=ctx)
                for product_id in qty.keys():
                    if not qty[product_id]:
                        continue
                    product = products_by_id[product_id]
                    quantity_total += qty[product_id]
                    price = qty[product_id] * product.standard_price
                    total_price += price
                    result['product'].append({
                        'price': product.standard_price,
                        'prod_name': product.name,
                        'code': product.default_code, # used by lot_overview_all report!
                        'variants': product.variants or '',
                        'uom': product.uom_id.name,
                        'prod_qty': qty[product_id],
                        'price_value': price,
                    })
        result['total'] = quantity_total
        result['total_price'] = total_price
        return result

    def _product_get_multi_location(self, cr, uid, ids, product_ids=False, context={}, states=['done'], what=('in', 'out')):
        product_obj = self.pool.get('product.product')
        context.update({
            'states': states,
            'what': what,
            'location': ids
        })
        return product_obj.get_product_available(cr, uid, product_ids, context=context)

    def _product_get(self, cr, uid, id, product_ids=False, context={}, states=['done']):
        ids = id and [id] or []
        return self._product_get_multi_location(cr, uid, ids, product_ids, context, states)

    def _product_all_get(self, cr, uid, id, product_ids=False, context={}, states=['done']):
        # build the list of ids of children of the location given by id
        ids = id and [id] or []
        location_ids = self.search(cr, uid, [('location_id', 'child_of', ids)])
        return self._product_get_multi_location(cr, uid, location_ids, product_ids, context, states)

    def _product_virtual_get(self, cr, uid, id, product_ids=False, context={}, states=['done']):
        return self._product_all_get(cr, uid, id, product_ids, context, ['confirmed', 'waiting', 'assigned', 'done'])

    #
    # TODO:
    #    Improve this function
    #
    # Returns:
    #    [ (tracking_id, product_qty, location_id) ]
    #
    def _product_reserve(self, cr, uid, ids, product_id, product_qty, context={}):
        result = []
        amount = 0.0
        for id in self.search(cr, uid, [('location_id', 'child_of', ids)]):
            cr.execute("select product_uom,sum(product_qty) as product_qty from stock_move where location_dest_id=%s and location_id<>%s and product_id=%s and state='done' group by product_uom", (id, id, product_id))
            results = cr.dictfetchall()
            cr.execute("select product_uom,-sum(product_qty) as product_qty from stock_move where location_id=%s and location_dest_id<>%s and product_id=%s and state in ('done', 'assigned') group by product_uom", (id, id, product_id))
            results += cr.dictfetchall()

            total = 0.0
            results2 = 0.0
            for r in results:
                amount = self.pool.get('product.uom')._compute_qty(cr, uid, r['product_uom'], r['product_qty'], context.get('uom', False))
                results2 += amount
                total += amount

            if total <= 0.0:
                continue

            amount = results2
            if amount > 0:
                if amount > min(total, product_qty):
                    amount = min(product_qty, total)
                result.append((amount, id))
                product_qty -= amount
                total -= amount
                if product_qty <= 0.0:
                    return result
                if total <= 0.0:
                    continue
        return False

stock_location()


class stock_tracking(osv.osv):
    _name = "stock.tracking"
    _description = "Stock Tracking Lots"

    def checksum(sscc):
        salt = '31' * 8 + '3'
        sum = 0
        for sscc_part, salt_part in zip(sscc, salt):
            sum += int(sscc_part) * int(salt_part)
        return (10 - (sum % 10)) % 10
    checksum = staticmethod(checksum)

    def make_sscc(self, cr, uid, context={}):
        sequence = self.pool.get('ir.sequence').get(cr, uid, 'stock.lot.tracking')
        return sequence + str(self.checksum(sequence))

    _columns = {
        'name': fields.char('Tracking', size=64, required=True),
        'active': fields.boolean('Active'),
        'serial': fields.char('Reference', size=64),
        'move_ids': fields.one2many('stock.move', 'tracking_id', 'Moves Tracked'),
        'date': fields.datetime('Date Created', required=True),
    }
    _defaults = {
        'active': lambda *a: 1,
        'name': make_sscc,
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
        if not args:
            args = []
        if not context:
            context = {}
        ids = self.search(cr, user, [('serial', '=', name)]+ args, limit=limit, context=context)
        ids += self.search(cr, user, [('name', operator, name)]+ args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

    def name_get(self, cr, uid, ids, context={}):
        if not len(ids):
            return []
        res = [(r['id'], r['name']+' ['+(r['serial'] or '')+']') for r in self.read(cr, uid, ids, ['name', 'serial'], context)]
        return res

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Error'), _('You can not remove a lot line !'))

stock_tracking()


#----------------------------------------------------------
# Stock Picking
#----------------------------------------------------------
class stock_picking(osv.osv):
    _name = "stock.picking"
    _description = "Picking List"

    def _set_maximum_date(self, cr, uid, ids, name, value, arg, context):
        if not value:
            return False
        if isinstance(ids, (int, long)):
            ids = [ids]
        for pick in self.browse(cr, uid, ids, context):
            sql_str = """update stock_move set
                    date_planned='%s'
                where
                    picking_id=%d """ % (value, pick.id)

            if pick.max_date:
                sql_str += " and (date_planned='" + pick.max_date + "' or date_planned>'" + value + "')"
            cr.execute(sql_str)
        return True

    def _set_minimum_date(self, cr, uid, ids, name, value, arg, context):
        if not value:
            return False
        if isinstance(ids, (int, long)):
            ids = [ids]
        for pick in self.browse(cr, uid, ids, context):
            sql_str = """update stock_move set
                    date_planned='%s'
                where
                    picking_id=%s """ % (value, pick.id)
            if pick.min_date:
                sql_str += " and (date_planned='" + pick.min_date + "' or date_planned<'" + value + "')"
            cr.execute(sql_str)
        return True

    def get_min_max_date(self, cr, uid, ids, field_name, arg, context={}):
        res = {}
        for id in ids:
            res[id] = {'min_date': False, 'max_date': False}
        if not ids:
            return res
        cr.execute("""select
                picking_id,
                min(date_planned),
                max(date_planned)
            from
                stock_move
            where
                picking_id in (""" + ','.join(map(str, ids)) + """)
            group by
                picking_id""")
        for pick, dt1, dt2 in cr.fetchall():
            res[pick]['min_date'] = dt1
            res[pick]['max_date'] = dt2
        return res

    def create(self, cr, user, vals, context=None):
        if ('name' not in vals) or (vals.get('name')=='/'):
            vals['name'] = self.pool.get('ir.sequence').get(cr, user, 'stock.picking')

        return super(stock_picking, self).create(cr, user, vals, context)

    _columns = {
        'name': fields.char('Reference', size=64, select=True),
        'origin': fields.char('Origin Reference', size=64),
        'backorder_id': fields.many2one('stock.picking', 'Back Order'),
        'type': fields.selection([('out', 'Sending Goods'), ('in', 'Getting Goods'), ('internal', 'Internal'), ('delivery', 'Delivery')], 'Shipping Type', required=True, select=True, help="Shipping type specify, goods coming in or going out."),
        'active': fields.boolean('Active'),
        'note': fields.text('Notes'),

        'location_id': fields.many2one('stock.location', 'Location', help="Keep empty if you produce at the location where the finished products are needed." \
                "Set a location if you produce at a fixed location. This can be a partner location " \
                "if you subcontract the manufacturing operations."),
        'location_dest_id': fields.many2one('stock.location', 'Dest. Location',help="Location where the system will stock the finished products."),
        'move_type': fields.selection([('direct', 'Direct Delivery'), ('one', 'All at once')], 'Delivery Method', required=True, help="It specifies goods to be delivered all at once or by direct delivery"),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('auto', 'Waiting'),
            ('confirmed', 'Confirmed'),
            ('assigned', 'Available'),
            ('done', 'Done'),
            ('cancel', 'Cancelled'),
            ], 'State', readonly=True, select=True,
            help=' * The \'Draft\' state is used when a user is encoding a new and unconfirmed picking. \
            \n* The \'Confirmed\' state is used for stock movement to do with unavailable products. \
            \n* The \'Available\' state is set automatically when the products are ready to be moved.\
            \n* The \'Waiting\' state is used in MTO moves when a movement is waiting for another one.'),
        'min_date': fields.function(get_min_max_date, fnct_inv=_set_minimum_date, multi="min_max_date",
                 method=True, store=True, type='datetime', string='Planned Date', select=1, help="Planned date for Picking. Default it takes current date"),
        'date': fields.datetime('Date Order', help="Date of Order"),
        'date_done': fields.datetime('Date Done', help="Date of completion"),
        'max_date': fields.function(get_min_max_date, fnct_inv=_set_maximum_date, multi="min_max_date",
                 method=True, store=True, type='datetime', string='Max. Planned Date', select=2),
        'move_lines': fields.one2many('stock.move', 'picking_id', 'Entry lines', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}),
        'auto_picking': fields.boolean('Auto-Picking'),
        'address_id': fields.many2one('res.partner.address', 'Partner', help="Address of partner"),
        'invoice_state': fields.selection([
            ("invoiced", "Invoiced"),
            ("2binvoiced", "To Be Invoiced"),
            ("none", "Not from Picking")], "Invoice Status",
            select=True, required=True, readonly=True, states={'draft': [('readonly', False)]}),
    }
    _defaults = {
        'name': lambda self, cr, uid, context: '/',
        'active': lambda *a: 1,
        'state': lambda *a: 'draft',
        'move_type': lambda *a: 'direct',
        'type': lambda *a: 'in',
        'invoice_state': lambda *a: 'none',
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    def copy(self, cr, uid, id, default=None, context={}):
        if default is None:
            default = {}
        default = default.copy()
        if not default.get('name',False):
            default['name'] = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking')
        return super(stock_picking, self).copy(cr, uid, id, default, context)

    def onchange_partner_in(self, cr, uid, context, partner_id=None):
        return {}

    def action_explode(self, cr, uid, moves, context={}):
        return moves

    def action_confirm(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state': 'confirmed'})
        todo = []
        for picking in self.browse(cr, uid, ids):
            for r in picking.move_lines:
                if r.state == 'draft':
                    todo.append(r.id)
        todo = self.action_explode(cr, uid, todo, context)
        if len(todo):
            self.pool.get('stock.move').action_confirm(cr, uid, todo, context)
        return True

    def test_auto_picking(self, cr, uid, ids):
        # TODO: Check locations to see if in the same location ?
        return True

    def button_confirm(self, cr, uid, ids, *args):
        for id in ids:
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'stock.picking', id, 'button_confirm', cr)
        self.force_assign(cr, uid, ids, *args)
        return True

    def action_assign(self, cr, uid, ids, *args):
        for pick in self.browse(cr, uid, ids):
            move_ids = [x.id for x in pick.move_lines if x.state == 'confirmed']
            self.pool.get('stock.move').action_assign(cr, uid, move_ids)
        return True

    def force_assign(self, cr, uid, ids, *args):
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids):
#           move_ids = [x.id for x in pick.move_lines if x.state == 'confirmed']
            move_ids = [x.id for x in pick.move_lines]
            self.pool.get('stock.move').force_assign(cr, uid, move_ids)
            wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
        return True

    def draft_force_assign(self, cr, uid, ids, *args):
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids):
            wf_service.trg_validate(uid, 'stock.picking', pick.id,
                'button_confirm', cr)
            #move_ids = [x.id for x in pick.move_lines]
            #self.pool.get('stock.move').force_assign(cr, uid, move_ids)
            #wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
        return True

    def draft_validate(self, cr, uid, ids, *args):
        wf_service = netsvc.LocalService("workflow")
        self.draft_force_assign(cr, uid, ids)
        for pick in self.browse(cr, uid, ids):
            move_ids = [x.id for x in pick.move_lines]
            self.pool.get('stock.move').force_assign(cr, uid, move_ids)
            wf_service.trg_write(uid, 'stock.picking', pick.id, cr)

            self.action_move(cr, uid, [pick.id])
            wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_done', cr)
        return True

    def cancel_assign(self, cr, uid, ids, *args):
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids):
            move_ids = [x.id for x in pick.move_lines]
            self.pool.get('stock.move').cancel_assign(cr, uid, move_ids)
            wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
        return True

    def action_assign_wkf(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state': 'assigned'})
        return True

    def test_finnished(self, cr, uid, ids):
        move_ids = self.pool.get('stock.move').search(cr, uid, [('picking_id', 'in', ids)])
        for move in self.pool.get('stock.move').browse(cr, uid, move_ids):
            if move.state not in ('done', 'cancel'):
                if move.product_qty != 0.0:
                    return False
                else:
                    move.write(cr, uid, [move.id], {'state': 'done'})
        return True

    def test_assigned(self, cr, uid, ids):
        ok = True
        for pick in self.browse(cr, uid, ids):
            mt = pick.move_type
            for move in pick.move_lines:
                if (move.state in ('confirmed', 'draft')) and (mt=='one'):
                    return False
                if (mt=='direct') and (move.state=='assigned') and (move.product_qty):
                    return True
                ok = ok and (move.state in ('cancel', 'done', 'assigned'))
        return ok

    def action_cancel(self, cr, uid, ids, context={}):
        for pick in self.browse(cr, uid, ids):
            ids2 = [move.id for move in pick.move_lines]
            self.pool.get('stock.move').action_cancel(cr, uid, ids2, context)
        self.write(cr, uid, ids, {'state': 'cancel', 'invoice_state': 'none'})
        return True

    #
    # TODO: change and create a move if not parents
    #
    def action_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'done', 'date_done': time.strftime('%Y-%m-%d %H:%M:%S')})
        return True

    def action_move(self, cr, uid, ids, context={}):
        for pick in self.browse(cr, uid, ids):
            todo = []
            for move in pick.move_lines:
                if move.state == 'assigned':
                    todo.append(move.id)

            if len(todo):
                self.pool.get('stock.move').action_done(cr, uid, todo,
                        context=context)
        return True

    def get_currency_id(self, cursor, user, picking):
        return False

    def _get_payment_term(self, cursor, user, picking):
        '''Return {'contact': address, 'invoice': address} for invoice'''
        partner_obj = self.pool.get('res.partner')
        partner = picking.address_id.partner_id
        return partner.property_payment_term and partner.property_payment_term.id or False

    def _get_address_invoice(self, cursor, user, picking):
        '''Return {'contact': address, 'invoice': address} for invoice'''
        partner_obj = self.pool.get('res.partner')
        partner = picking.address_id.partner_id

        return partner_obj.address_get(cursor, user, [partner.id],
                ['contact', 'invoice'])

    def _get_comment_invoice(self, cursor, user, picking):
        '''Return comment string for invoice'''
        return picking.note or ''

    def _get_price_unit_invoice(self, cursor, user, move_line, type):
        '''Return the price unit for the move line'''
        if type in ('in_invoice', 'in_refund'):
            return move_line.product_id.standard_price
        else:
            return move_line.product_id.list_price

    def _get_discount_invoice(self, cursor, user, move_line):
        '''Return the discount for the move line'''
        return 0.0

    def _get_taxes_invoice(self, cursor, user, move_line, type):
        '''Return taxes ids for the move line'''
        if type in ('in_invoice', 'in_refund'):
            taxes = move_line.product_id.supplier_taxes_id
        else:
            taxes = move_line.product_id.taxes_id

        if move_line.picking_id and move_line.picking_id.address_id and move_line.picking_id.address_id.partner_id:
            return self.pool.get('account.fiscal.position').map_tax(
                cursor,
                user,
                move_line.picking_id.address_id.partner_id.property_account_position,
                taxes
            )
        else:
            return map(lambda x: x.id, taxes)

    def _get_account_analytic_invoice(self, cursor, user, picking, move_line):
        return False

    def _invoice_line_hook(self, cursor, user, move_line, invoice_line_id):
        '''Call after the creation of the invoice line'''
        return

    def _invoice_hook(self, cursor, user, picking, invoice_id):
        '''Call after the creation of the invoice'''
        return

    def action_invoice_create(self, cursor, user, ids, journal_id=False,
            group=False, type='out_invoice', context=None):
        '''Return ids of created invoices for the pickings'''
        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        invoices_group = {}
        res = {}

        for picking in self.browse(cursor, user, ids, context=context):
            if picking.invoice_state != '2binvoiced':
                continue
            payment_term_id = False
            partner = picking.address_id and picking.address_id.partner_id
            if not partner:
                raise osv.except_osv(_('Error, no partner !'),
                    _('Please put a partner on the picking list if you want to generate invoice.'))

            if type in ('out_invoice', 'out_refund'):
                account_id = partner.property_account_receivable.id
                payment_term_id = self._get_payment_term(cursor, user, picking)
            else:
                account_id = partner.property_account_payable.id

            address_contact_id, address_invoice_id = \
                    self._get_address_invoice(cursor, user, picking).values()

            comment = self._get_comment_invoice(cursor, user, picking)
            if group and partner.id in invoices_group:
                invoice_id = invoices_group[partner.id]
                invoice = invoice_obj.browse(cursor, user, invoice_id)
                invoice_vals = {
                    'name': (invoice.name or '') + ', ' + (picking.name or ''),
                    'origin': (invoice.origin or '') + ', ' + (picking.name or '') + (picking.origin and (':' + picking.origin) or ''),
                    'comment': (comment and (invoice.comment and invoice.comment+"\n"+comment or comment)) or (invoice.comment and invoice.comment or ''),
                    'date_invoice':context.get('date_inv',False)
                }
                invoice_obj.write(cursor, user, [invoice_id], invoice_vals, context=context)
            else:
                invoice_vals = {
                    'name': picking.name,
                    'origin': (picking.name or '') + (picking.origin and (':' + picking.origin) or ''),
                    'type': type,
                    'account_id': account_id,
                    'partner_id': partner.id,
                    'address_invoice_id': address_invoice_id,
                    'address_contact_id': address_contact_id,
                    'comment': comment,
                    'payment_term': payment_term_id,
                    'fiscal_position': partner.property_account_position.id,
                    'date_invoice':context.get('date_inv',False)
                    }
                cur_id = self.get_currency_id(cursor, user, picking)
                if cur_id:
                    invoice_vals['currency_id'] = cur_id
                if journal_id:
                    invoice_vals['journal_id'] = journal_id
                invoice_id = invoice_obj.create(cursor, user, invoice_vals,
                        context=context)
                invoices_group[partner.id] = invoice_id
            res[picking.id] = invoice_id
            for move_line in picking.move_lines:
                origin = move_line.picking_id.name
                if move_line.picking_id.origin:
                    origin += ':' + move_line.picking_id.origin
                if group:
                    name = (picking.name or '') + '-' + move_line.name
                else:
                    name = move_line.name

                if type in ('out_invoice', 'out_refund'):
                    account_id = move_line.product_id.product_tmpl_id.\
                            property_account_income.id
                    if not account_id:
                        account_id = move_line.product_id.categ_id.\
                                property_account_income_categ.id
                else:
                    account_id = move_line.product_id.product_tmpl_id.\
                            property_account_expense.id
                    if not account_id:
                        account_id = move_line.product_id.categ_id.\
                                property_account_expense_categ.id

                price_unit = self._get_price_unit_invoice(cursor, user,
                        move_line, type)
                discount = self._get_discount_invoice(cursor, user, move_line)
                tax_ids = self._get_taxes_invoice(cursor, user, move_line, type)
                account_analytic_id = self._get_account_analytic_invoice(cursor,
                        user, picking, move_line)

                account_id = self.pool.get('account.fiscal.position').map_account(cursor, user, partner.property_account_position, account_id)
                notes = False
                if move_line.sale_line_id:
                    notes = move_line.sale_line_id.notes
                elif move_line.purchase_line_id:
                    notes = move_line.purchase_line_id.notes

                invoice_line_id = invoice_line_obj.create(cursor, user, {
                    'name': name,
                    'origin': origin,
                    'invoice_id': invoice_id,
                    'uos_id': move_line.product_uos.id,
                    'product_id': move_line.product_id.id,
                    'account_id': account_id,
                    'price_unit': price_unit,
                    'discount': discount,
                    'quantity': move_line.product_uos_qty or move_line.product_qty,
                    'invoice_line_tax_id': [(6, 0, tax_ids)],
                    'account_analytic_id': account_analytic_id,
                    'note': notes,
                    }, context=context)
                self._invoice_line_hook(cursor, user, move_line, invoice_line_id)

            invoice_obj.button_compute(cursor, user, [invoice_id], context=context,
                    set_total=(type in ('in_invoice', 'in_refund')))
            self.write(cursor, user, [picking.id], {
                'invoice_state': 'invoiced',
                }, context=context)
            self._invoice_hook(cursor, user, picking, invoice_id)
        self.write(cursor, user, res.keys(), {
            'invoice_state': 'invoiced',
            }, context=context)
        return res

    def test_cancel(self, cr, uid, ids, context={}):
        for pick in self.browse(cr, uid, ids, context=context):
            if not pick.move_lines:
                return False
            for move in pick.move_lines:
                if move.state not in ('cancel',):
                    return False
        return True

stock_picking()


class stock_production_lot(osv.osv):
    def name_get(self, cr, uid, ids, context={}):
        if not ids:
            return []
        reads = self.read(cr, uid, ids, ['name', 'ref'], context)
        res = []
        for record in reads:
            name = record['name']
            if record['ref']:
                name = name + '/' + record['ref']
            res.append((record['id'], name))
        return res

    _name = 'stock.production.lot'
    _description = 'Production lot'

    def _get_stock(self, cr, uid, ids, field_name, arg, context={}):
        if 'location_id' not in context:
            locations = self.pool.get('stock.location').search(cr, uid, [('usage', '=', 'internal')], context=context)
        else:
            locations = context['location_id'] and [context['location_id']] or []

        if isinstance(ids, (int, long)):
            ids = [ids]

        res = {}.fromkeys(ids, 0.0)

        if locations:
            cr.execute('''select
                    prodlot_id,
                    sum(name)
                from
                    stock_report_prodlots
                where
                    location_id in ('''+','.join(map(str, locations))+''')  and
                    prodlot_id in  ('''+','.join(map(str, ids))+''')
                group by
                    prodlot_id
            ''')
            res.update(dict(cr.fetchall()))
        return res

    def _stock_search(self, cr, uid, obj, name, args):
        locations = self.pool.get('stock.location').search(cr, uid, [('usage', '=', 'internal')])
        cr.execute('''select
                prodlot_id,
                sum(name)
            from
                stock_report_prodlots
            where
                location_id in ('''+','.join(map(str, locations)) + ''')
            group by
                prodlot_id
            having  sum(name)  ''' + str(args[0][1]) + ''' ''' + str(args[0][2])
        )
        res = cr.fetchall()
        ids = [('id', 'in', map(lambda x: x[0], res))]
        return ids

    _columns = {
        'name': fields.char('Serial', size=64, required=True),
        'ref': fields.char('Internal Ref', size=64),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'date': fields.datetime('Created Date', required=True),
        'stock_available': fields.function(_get_stock, fnct_search=_stock_search, method=True, type="float", string="Available", select="2"),
        'revisions': fields.one2many('stock.production.lot.revision', 'lot_id', 'Revisions'),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'name': lambda x, y, z, c: x.pool.get('ir.sequence').get(y, z, 'stock.lot.serial'),
        'product_id': lambda x, y, z, c: c.get('product_id', False),
    }
    _sql_constraints = [
        ('name_ref_uniq', 'unique (name, ref)', 'The serial/ref must be unique !'),
    ]

stock_production_lot()


class stock_production_lot_revision(osv.osv):
    _name = 'stock.production.lot.revision'
    _description = 'Production lot revisions'
    _columns = {
        'name': fields.char('Revision Name', size=64, required=True),
        'description': fields.text('Description'),
        'date': fields.date('Revision Date'),
        'indice': fields.char('Revision', size=16),
        'author_id': fields.many2one('res.users', 'Author'),
        'lot_id': fields.many2one('stock.production.lot', 'Production lot', select=True, ondelete='cascade'),
    }

    _defaults = {
        'author_id': lambda x, y, z, c: z,
        'date': lambda *a: time.strftime('%Y-%m-%d'),
    }

stock_production_lot_revision()

# ----------------------------------------------------
# Move
# ----------------------------------------------------

#
# Fields:
#   location_dest_id is only used for predicting futur stocks
#
class stock_move(osv.osv):
    def _getSSCC(self, cr, uid, context={}):
        cr.execute('select id from stock_tracking where create_uid=%s order by id desc limit 1', (uid,))
        res = cr.fetchone()
        return (res and res[0]) or False
    _name = "stock.move"
    _description = "Stock Move"

    def name_get(self, cr, uid, ids, context={}):
        res = []
        for line in self.browse(cr, uid, ids, context):
            res.append((line.id, (line.product_id.code or '/')+': '+line.location_id.name+' > '+line.location_dest_id.name))
        return res

    def _check_tracking(self, cr, uid, ids):
        for move in self.browse(cr, uid, ids):
            if not move.prodlot_id and \
               (move.state == 'done' and \
               ( \
                   (move.product_id.track_production and move.location_id.usage=='production') or \
                   (move.product_id.track_production and move.location_dest_id.usage=='production') or \
                   (move.product_id.track_incoming and move.location_id.usage=='supplier') or \
                   (move.product_id.track_outgoing and move.location_dest_id.usage=='customer') \
               )):
                return False
        return True

    def _check_product_lot(self, cr, uid, ids):
        for move in self.browse(cr, uid, ids):
            if move.prodlot_id and (move.prodlot_id.product_id.id != move.product_id.id):
                return False
        return True

    _columns = {
        'name': fields.char('Name', size=64, required=True, select=True),
        'priority': fields.selection([('0', 'Not urgent'), ('1', 'Urgent')], 'Priority'),

        'date': fields.datetime('Date Created'),
        'date_planned': fields.datetime('Date', required=True, help="Scheduled date for the movement of the products or real date if the move is done."),

        'product_id': fields.many2one('product.product', 'Product', required=True, select=True),

        'product_qty': fields.float('Quantity', required=True),
        'product_uom': fields.many2one('product.uom', 'Product UOM', required=True),
        'product_uos_qty': fields.float('Quantity (UOS)'),
        'product_uos': fields.many2one('product.uom', 'Product UOS'),
        'product_packaging': fields.many2one('product.packaging', 'Packaging', help="It specifies attributes of packaging like type, quantity of packaging,etc."),

        'location_id': fields.many2one('stock.location', 'Source Location', required=True, select=True, help="Set a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations."),
        'location_dest_id': fields.many2one('stock.location', 'Dest. Location', required=True, select=True, help="Location where the system will stock the finished products."),
        'address_id': fields.many2one('res.partner.address', 'Dest. Address', help="Adress where goods are to be delivered"),

        'prodlot_id': fields.many2one('stock.production.lot', 'Production Lot', help="Production lot is used to put a serial number on the production"),
        'tracking_id': fields.many2one('stock.tracking', 'Tracking Lot', select=True, help="Tracking lot is the code that will be put on the logistical unit/pallet"),
#       'lot_id': fields.many2one('stock.lot', 'Consumer lot', select=True, readonly=True),

        'auto_validate': fields.boolean('Auto Validate'),

        'move_dest_id': fields.many2one('stock.move', 'Dest. Move'),
        'move_history_ids': fields.many2many('stock.move', 'stock_move_history_ids', 'parent_id', 'child_id', 'Move History'),
        'move_history_ids2': fields.many2many('stock.move', 'stock_move_history_ids', 'child_id', 'parent_id', 'Move History'),
        'picking_id': fields.many2one('stock.picking', 'Picking List', select=True),

        'note': fields.text('Notes'),

        'state': fields.selection([('draft', 'Draft'), ('waiting', 'Waiting'), ('confirmed', 'Confirmed'), ('assigned', 'Available'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', readonly=True, select=True,
                                  help='When the stock move is created it is in the \'Draft\' state.\n After that it is set to \'Confirmed\' state.\n If stock is available state is set to \'Avaiable\'.\n When the packing it done the state is \'Done\'.\
                                  \nThe state is \'Waiting\' if the move is waiting for another one.'),
        'price_unit': fields.float('Unit Price',
            digits=(16, int(config['price_accuracy']))),
    }
    _constraints = [
        (_check_tracking,
            'You must assign a production lot for this product',
            ['prodlot_id']),
        (_check_product_lot,
            'You try to assign a lot which is not from the same product',
            ['prodlot_id'])]

    def _default_location_destination(self, cr, uid, context={}):
        if context.get('move_line', []):
            if context['move_line'][0]:
                if isinstance(context['move_line'][0], (tuple, list)):
                    return context['move_line'][0][2] and context['move_line'][0][2]['location_dest_id'] or False
                else:
                    move_list = self.pool.get('stock.move').read(cr, uid, context['move_line'][0], ['location_dest_id'])
                    return move_list and move_list['location_dest_id'][0] or False
        if context.get('address_out_id', False):
            return self.pool.get('res.partner.address').browse(cr, uid, context['address_out_id'], context).partner_id.property_stock_customer.id
        return False

    def _default_location_source(self, cr, uid, context={}):
        if context.get('move_line', []):
            try:
                return context['move_line'][0][2]['location_id']
            except:
                pass
        if context.get('address_in_id', False):
            return self.pool.get('res.partner.address').browse(cr, uid, context['address_in_id'], context).partner_id.property_stock_supplier.id
        return False

    _defaults = {
        'location_id': _default_location_source,
        'location_dest_id': _default_location_destination,
        'state': lambda *a: 'draft',
        'priority': lambda *a: '1',
        'product_qty': lambda *a: 1.0,
        'date_planned': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    def _auto_init(self, cursor, context):
        res = super(stock_move, self)._auto_init(cursor, context)
        cursor.execute('SELECT indexname \
                FROM pg_indexes \
                WHERE indexname = \'stock_move_location_id_location_dest_id_product_id_state\'')
        if not cursor.fetchone():
            cursor.execute('CREATE INDEX stock_move_location_id_location_dest_id_product_id_state \
                    ON stock_move (location_id, location_dest_id, product_id, state)')
            cursor.commit()
        return res

    def onchange_lot_id(self, cr, uid, ids, prodlot_id=False, product_qty=False, loc_id=False, context=None):
        if not prodlot_id or not loc_id:
            return {}
        ctx = context and context.copy() or {}
        ctx['location_id'] = loc_id
        prodlot = self.pool.get('stock.production.lot').browse(cr, uid, prodlot_id, ctx)
        location = self.pool.get('stock.location').browse(cr, uid, loc_id)
        warning = {}
        if (location.usage == 'internal') and (product_qty > (prodlot.stock_available or 0.0)):
            warning = {
                'title': 'Bad Lot Assignation !',
                'message': 'You are moving %.2f products but only %.2f available in this lot.' % (product_qty, prodlot.stock_available or 0.0)
            }
        return {'warning': warning}

    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False, loc_dest_id=False):
        if not prod_id:
            return {}
        product = self.pool.get('product.product').browse(cr, uid, [prod_id])[0]
        result = {
            'name': product.name,
            'product_uom': product.uom_id.id,
        }
        if loc_id:
            result['location_id'] = loc_id
        if loc_dest_id:
            result['location_dest_id'] = loc_dest_id
        return {'value': result}

    def _chain_compute(self, cr, uid, moves, context={}):
        result = {}
        for m in moves:
            dest = self.pool.get('stock.location').chained_location_get(
                cr,
                uid,
                m.location_dest_id,
                m.picking_id and m.picking_id.address_id and m.picking_id.address_id.partner_id,
                m.product_id,
                context
            )
            if dest:
                if dest[1] == 'transparent':
                    self.write(cr, uid, [m.id], {
                        'date_planned': (DateTime.strptime(m.date_planned, '%Y-%m-%d %H:%M:%S') + \
                            DateTime.RelativeDateTime(days=dest[2] or 0)).strftime('%Y-%m-%d'),
                        'location_dest_id': dest[0].id})
                else:
                    result.setdefault(m.picking_id, [])
                    result[m.picking_id].append( (m, dest) )
        return result

    def action_confirm(self, cr, uid, ids, context={}):
#        ids = map(lambda m: m.id, moves)
        moves = self.browse(cr, uid, ids)
        self.write(cr, uid, ids, {'state': 'confirmed'})
        i = 0

        def create_chained_picking(self, cr, uid, moves, context):
            new_moves = []
            for picking, todo in self._chain_compute(cr, uid, moves, context).items():
                ptype = self.pool.get('stock.location').picking_type_get(cr, uid, todo[0][0].location_dest_id, todo[0][1][0])
                pickid = self.pool.get('stock.picking').create(cr, uid, {
                    'name': picking.name,
                    'origin': str(picking.origin or ''),
                    'type': ptype,
                    'note': picking.note,
                    'move_type': picking.move_type,
                    'auto_picking': todo[0][1][1] == 'auto',
                    'address_id': picking.address_id.id,
                    'invoice_state': 'none'
                })
                for move, (loc, auto, delay) in todo:
                    # Is it smart to copy ? May be it's better to recreate ?
                    new_id = self.pool.get('stock.move').copy(cr, uid, move.id, {
                        'location_id': move.location_dest_id.id,
                        'location_dest_id': loc.id,
                        'date_moved': time.strftime('%Y-%m-%d'),
                        'picking_id': pickid,
                        'state': 'waiting',
                        'move_history_ids': [],
                        'date_planned': (DateTime.strptime(move.date_planned, '%Y-%m-%d %H:%M:%S') + DateTime.RelativeDateTime(days=delay or 0)).strftime('%Y-%m-%d'),
                        'move_history_ids2': []}
                    )
                    self.pool.get('stock.move').write(cr, uid, [move.id], {
                        'move_dest_id': new_id,
                        'move_history_ids': [(4, new_id)]
                    })
                    new_moves.append(self.browse(cr, uid, [new_id])[0])
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_validate(uid, 'stock.picking', pickid, 'button_confirm', cr)
            if new_moves:
                create_chained_picking(self, cr, uid, new_moves, context)
        create_chained_picking(self, cr, uid, moves, context)
        return []

    def action_assign(self, cr, uid, ids, *args):
        todo = []
        for move in self.browse(cr, uid, ids):
            if move.state in ('confirmed', 'waiting'):
                todo.append(move.id)
        res = self.check_assign(cr, uid, todo)
        return res

    def force_assign(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state': 'assigned'})
        return True

    def cancel_assign(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state': 'confirmed'})
        return True

    #
    # Duplicate stock.move
    #
    def check_assign(self, cr, uid, ids, context={}):
        done = []
        count = 0
        pickings = {}
        for move in self.browse(cr, uid, ids):
            if move.product_id.type == 'consu':
                if move.state in ('confirmed', 'waiting'):
                    done.append(move.id)
                pickings[move.picking_id.id] = 1
                continue
            if move.state in ('confirmed', 'waiting'):
                res = self.pool.get('stock.location')._product_reserve(cr, uid, [move.location_id.id], move.product_id.id, move.product_qty, {'uom': move.product_uom.id})
                if res:
                    #_product_available_test depends on the next status for correct functioning
                    #the test does not work correctly if the same product occurs multiple times
                    #in the same order. This is e.g. the case when using the button 'split in two' of
                    #the stock outgoing form
                    self.write(cr, uid, move.id, {'state':'assigned'})
                    done.append(move.id)
                    pickings[move.picking_id.id] = 1
                    r = res.pop(0)
                    cr.execute('update stock_move set location_id=%s, product_qty=%s where id=%s', (r[1], r[0], move.id))

                    while res:
                        r = res.pop(0)
                        move_id = self.copy(cr, uid, move.id, {'product_qty': r[0], 'location_id': r[1]})
                        done.append(move_id)
                        #cr.execute('insert into stock_move_history_ids values (%s,%s)', (move.id,move_id))
        if done:
            count += len(done)
            self.write(cr, uid, done, {'state': 'assigned'})

        if count:
            for pick_id in pickings:
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_write(uid, 'stock.picking', pick_id, cr)
        return count

    #
    # Cancel move => cancel others move and pickings
    #
    def action_cancel(self, cr, uid, ids, context={}):
        if not len(ids):
            return True
        pickings = {}
        for move in self.browse(cr, uid, ids):
            if move.state in ('confirmed', 'waiting', 'assigned', 'draft'):
                if move.picking_id:
                    pickings[move.picking_id.id] = True
            if move.move_dest_id and move.move_dest_id.state == 'waiting':
                self.write(cr, uid, [move.move_dest_id.id], {'state': 'assigned'})
                if move.move_dest_id.picking_id:
                    wf_service = netsvc.LocalService("workflow")
                    wf_service.trg_write(uid, 'stock.picking', move.move_dest_id.picking_id.id, cr)
        self.write(cr, uid, ids, {'state': 'cancel', 'move_dest_id': False})

        for pick in self.pool.get('stock.picking').browse(cr, uid, pickings.keys()):
            if all(move.state == 'cancel' for move in pick.move_lines):
                self.pool.get('stock.picking').write(cr, uid, [pick.id], {'state': 'cancel'})

        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_trigger(uid, 'stock.move', id, cr)
        #self.action_cancel(cr,uid, ids2, context)
        return True

    def action_done(self, cr, uid, ids, context=None):
        track_flag = False
        for move in self.browse(cr, uid, ids):
            if move.move_dest_id.id and (move.state != 'done'):
                cr.execute('insert into stock_move_history_ids (parent_id,child_id) values (%s,%s)', (move.id, move.move_dest_id.id))
                if move.move_dest_id.state in ('waiting', 'confirmed'):
                    self.write(cr, uid, [move.move_dest_id.id], {'state': 'assigned'})
                    if move.move_dest_id.picking_id:
                        wf_service = netsvc.LocalService("workflow")
                        wf_service.trg_write(uid, 'stock.picking', move.move_dest_id.picking_id.id, cr)
                    else:
                        pass
                        # self.action_done(cr, uid, [move.move_dest_id.id])
                    if move.move_dest_id.auto_validate:
                        self.action_done(cr, uid, [move.move_dest_id.id], context=context)

            #
            # Accounting Entries
            #
            acc_src = None
            acc_dest = None
            if move.location_id.account_id:
                acc_src = move.location_id.account_id.id
            if move.location_dest_id.account_id:
                acc_dest = move.location_dest_id.account_id.id
            if acc_src or acc_dest:
                test = [('product.product', move.product_id.id)]
                if move.product_id.categ_id:
                    test.append( ('product.category', move.product_id.categ_id.id) )
                if not acc_src:
                    acc_src = move.product_id.product_tmpl_id.\
                            property_stock_account_input.id
                    if not acc_src:
                        acc_src = move.product_id.categ_id.\
                                property_stock_account_input_categ.id
                    if not acc_src:
                        raise osv.except_osv(_('Error!'),
                                _('There is no stock input account defined ' \
                                        'for this product: "%s" (id: %d)') % \
                                        (move.product_id.name,
                                            move.product_id.id,))
                if not acc_dest:
                    acc_dest = move.product_id.product_tmpl_id.\
                            property_stock_account_output.id
                    if not acc_dest:
                        acc_dest = move.product_id.categ_id.\
                                property_stock_account_output_categ.id
                    if not acc_dest:
                        raise osv.except_osv(_('Error!'),
                                _('There is no stock output account defined ' \
                                        'for this product: "%s" (id: %d)') % \
                                        (move.product_id.name,
                                            move.product_id.id,))
                if not move.product_id.categ_id.property_stock_journal.id:
                    raise osv.except_osv(_('Error!'),
                        _('There is no journal defined '\
                            'on the product category: "%s" (id: %d)') % \
                            (move.product_id.categ_id.name,
                                move.product_id.categ_id.id,))
                journal_id = move.product_id.categ_id.property_stock_journal.id
                if acc_src != acc_dest:
                    ref = move.picking_id and move.picking_id.name or False
                    product_uom_obj = self.pool.get('product.uom')
                    default_uom = move.product_id.uom_id.id
                    q = product_uom_obj._compute_qty(cr, uid, move.product_uom.id, move.product_qty, default_uom)
                    if move.product_id.cost_method == 'average' and move.price_unit:
                        amount = q * move.price_unit
                    else:
                        amount = q * move.product_id.standard_price

                    date = time.strftime('%Y-%m-%d')
                    partner_id = False
                    if move.picking_id:
                        partner_id = move.picking_id.address_id and (move.picking_id.address_id.partner_id and move.picking_id.address_id.partner_id.id or False) or False
                    lines = [
                            (0, 0, {
                                'name': move.name,
                                'quantity': move.product_qty,
                                'product_id': move.product_id and move.product_id.id or False,
                                'credit': amount,
                                'account_id': acc_src,
                                'ref': ref,
                                'date': date,
                                'partner_id': partner_id}),
                            (0, 0, {
                                'name': move.name,
                                'product_id': move.product_id and move.product_id.id or False,
                                'quantity': move.product_qty,
                                'debit': amount,
                                'account_id': acc_dest,
                                'ref': ref,
                                'date': date,
                                'partner_id': partner_id})
                    ]
                    self.pool.get('account.move').create(cr, uid, {
                        'name': move.name,
                        'journal_id': journal_id,
                        'line_id': lines,
                        'ref': ref,
                    })
        self.write(cr, uid, ids, {'state': 'done', 'date_planned': time.strftime('%Y-%m-%d %H:%M:%S')})
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_trigger(uid, 'stock.move', id, cr)
        return True

    def unlink(self, cr, uid, ids, context=None):
        for move in self.browse(cr, uid, ids, context=context):
            if move.state != 'draft':
                raise osv.except_osv(_('UserError'),
                        _('You can only delete draft moves.'))
        return super(stock_move, self).unlink(
            cr, uid, ids, context=context)

stock_move()


class stock_inventory(osv.osv):
    _name = "stock.inventory"
    _description = "Inventory"
    _columns = {
        'name': fields.char('Inventory', size=64, required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'date': fields.datetime('Date create', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'date_done': fields.datetime('Date done'),
        'inventory_line_id': fields.one2many('stock.inventory.line', 'inventory_id', 'Inventories', readonly=True, states={'draft': [('readonly', False)]}),
        'move_ids': fields.many2many('stock.move', 'stock_inventory_move_rel', 'inventory_id', 'move_id', 'Created Moves'),
        'state': fields.selection( (('draft', 'Draft'), ('done', 'Done'), ('cancel','Cancelled')), 'State', readonly=True),
        'company_id': fields.many2one('res.company','Company',required=True),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'state': lambda *a: 'draft',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.inventory', c)
    }

    #
    # Update to support tracking
    #
    def action_done(self, cr, uid, ids, context=None):
        for inv in self.browse(cr, uid, ids):
            move_ids = []
            move_line = []
            for line in inv.inventory_line_id:
                pid = line.product_id.id
                price = line.product_id.standard_price or 0.0
                amount = self.pool.get('stock.location')._product_get(cr, uid, line.location_id.id, [pid], {'uom': line.product_uom.id})[pid]
                change = line.product_qty - amount
                if change:
                    location_id = line.product_id.product_tmpl_id.property_stock_inventory.id
                    value = {
                        'name': 'INV:' + str(line.inventory_id.id) + ':' + line.inventory_id.name,
                        'product_id': line.product_id.id,
                        'product_uom': line.product_uom.id,
                        'date': inv.date,
                        'date_planned': inv.date,
                        'state': 'assigned'
                    }
                    if change > 0:
                        value.update( {
                            'product_qty': change,
                            'location_id': location_id,
                            'location_dest_id': line.location_id.id,
                        })
                    else:
                        value.update( {
                            'product_qty': -change,
                            'location_id': line.location_id.id,
                            'location_dest_id': location_id,
                        })
                    move_ids.append(self.pool.get('stock.move').create(cr, uid, value))
            if len(move_ids):
                self.pool.get('stock.move').action_done(cr, uid, move_ids,
                        context=context)
            self.write(cr, uid, [inv.id], {'state': 'done', 'date_done': time.strftime('%Y-%m-%d %H:%M:%S'), 'move_ids': [(6, 0, move_ids)]})
        return True

    def action_cancel(self, cr, uid, ids, context={}):
        for inv in self.browse(cr, uid, ids):
            self.pool.get('stock.move').action_cancel(cr, uid, [x.id for x in inv.move_ids], context)
            self.write(cr, uid, [inv.id], {'state': 'draft'})
        return True

    def action_cancel_inventary(self, cr, uid, ids, context={}):
        for inv in self.browse(cr,uid,ids):
            self.pool.get('stock.move').action_cancel(cr, uid, [x.id for x in inv.move_ids], context)
            self.write(cr, uid, [inv.id], {'state':'cancel'})
        return True

stock_inventory()


class stock_inventory_line(osv.osv):
    _name = "stock.inventory.line"
    _description = "Inventory line"
    _columns = {
        'inventory_id': fields.many2one('stock.inventory', 'Inventory', ondelete='cascade', select=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_uom': fields.many2one('product.uom', 'Product UOM', required=True),
        'product_qty': fields.float('Quantity'),
        'company_id': fields.related('inventory_id','company_id',type='many2one',object='res.company',string='Company')
    }

    def on_change_product_id(self, cr, uid, ids, location_id, product, uom=False):
        if not product:
            return {}
        if not uom:
            prod = self.pool.get('product.product').browse(cr, uid, [product], {'uom': uom})[0]
            uom = prod.uom_id.id
        amount = self.pool.get('stock.location')._product_get(cr, uid, location_id, [product], {'uom': uom})[product]
        result = {'product_qty': amount, 'product_uom': uom}
        return {'value': result}

stock_inventory_line()


#----------------------------------------------------------
# Stock Warehouse
#----------------------------------------------------------
class stock_warehouse(osv.osv):
    _name = "stock.warehouse"
    _description = "Warehouse"
    _columns = {
        'name': fields.char('Name', size=60, required=True),
#       'partner_id': fields.many2one('res.partner', 'Owner'),
        'company_id': fields.many2one('res.company','Company',required=True),
        'partner_address_id': fields.many2one('res.partner.address', 'Owner Address'),
        'lot_input_id': fields.many2one('stock.location', 'Location Input', required=True),
        'lot_stock_id': fields.many2one('stock.location', 'Location Stock', required=True),
        'lot_output_id': fields.many2one('stock.location', 'Location Output', required=True),
    }
    _defaults = {
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.inventory', c)
    }
stock_warehouse()


# Move wizard :
#    get confirm or assign stock move lines of partner and put in current picking.
class stock_picking_move_wizard(osv.osv_memory):
    _name = 'stock.picking.move.wizard'

    def _get_picking(self, cr, uid, ctx):
        if ctx.get('action_id', False):
            return ctx['action_id']
        return False

    def _get_picking_address(self, cr, uid, ctx):
        picking_obj = self.pool.get('stock.picking')
        if ctx.get('action_id', False):
            picking = picking_obj.browse(cr, uid, [ctx['action_id']])[0]
            return picking.address_id and picking.address_id.id or False
        return False

    _columns = {
        'name': fields.char('Name', size=64, invisible=True),
        #'move_lines': fields.one2many('stock.move', 'picking_id', 'Move lines',readonly=True),
        'move_ids': fields.many2many('stock.move', 'picking_move_wizard_rel', 'picking_move_wizard_id', 'move_id', 'Entry lines', required=True),
        'address_id': fields.many2one('res.partner.address', 'Dest. Address', invisible=True),
        'picking_id': fields.many2one('stock.picking', 'Picking list', select=True, invisible=True),
    }
    _defaults = {
        'picking_id': _get_picking,
        'address_id': _get_picking_address,
    }

    def action_move(self, cr, uid, ids, context=None):
        move_obj = self.pool.get('stock.move')
        picking_obj = self.pool.get('stock.picking')
        for act in self.read(cr, uid, ids):
            move_lines = move_obj.browse(cr, uid, act['move_ids'])
            for line in move_lines:
                if line.picking_id:
                    picking_obj.write(cr, uid, [line.picking_id.id], {'move_lines': [(1, line.id, {'picking_id': act['picking_id']})]})
                    picking_obj.write(cr, uid, [act['picking_id']], {'move_lines': [(1, line.id, {'picking_id': act['picking_id']})]})
                    cr.commit()
                    old_picking = picking_obj.read(cr, uid, [line.picking_id.id])[0]
                    if not len(old_picking['move_lines']):
                        picking_obj.write(cr, uid, [old_picking['id']], {'state': 'done'})
                else:
                    raise osv.except_osv(_('UserError'),
                        _('You can not create new moves.'))
        return {'type': 'ir.actions.act_window_close'}

stock_picking_move_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
