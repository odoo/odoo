##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2014 OpenERP S.A. (<http://www.openerp.com>).
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

import logging
from openerp import SUPERUSER_ID
from openerp.osv import fields, osv

_logger = logging.getLogger(__name__)


class product_template(osv.osv):
    _name = 'product.template'
    _inherit = 'product.template'


    def compute_price(self, cr, uid, product_ids, template_ids=False, recursive=False, test=False, real_time_accounting = False, context=None):
        '''
        Will return test dict when the test = False
        Multiple ids at once?
        testdict is used to inform the user about the changes to be made
        '''
        testdict = {}
        if product_ids:
            ids = product_ids
            model = 'product.product'
        else:
            ids = template_ids
            model = 'product.template'
        for prod_id in ids:
            bom_obj = self.pool.get('mrp.bom')
            if model == 'product.product':
                bom_id = bom_obj._bom_find(cr, uid, product_id=prod_id, context=context)
            else:
                bom_id = bom_obj._bom_find(cr, uid, product_tmpl_id=prod_id, context=context)
            if bom_id:
                # In recursive mode, it will first compute the prices of child boms
                if recursive:
                    #Search the products that are components of this bom of prod_id
                    bom = bom_obj.browse(cr, uid, bom_id, context=context)

                    #Call compute_price on these subproducts
                    prod_set = set([x.product_id.id for x in bom.bom_line_ids])
                    res = self.compute_price(cr, uid, list(prod_set), recursive=recursive, test=test, real_time_accounting = real_time_accounting, context=context)
                    if test: 
                        testdict.update(res)
                #Use calc price to calculate and put the price on the product of the BoM if necessary
                price = self._calc_price(cr, uid, bom_obj.browse(cr, uid, bom_id, context=context), test=test, real_time_accounting = real_time_accounting, context=context)
                if test:
                    testdict.update({prod_id : price})
        if test:
            return testdict
        else:
            return True


    def _calc_price(self, cr, uid, bom, test = False, real_time_accounting=False, context=None):
        if context is None:
            context={}
        price = 0
        uom_obj = self.pool.get("product.uom")
        tmpl_obj = self.pool.get('product.template')
        for sbom in bom.bom_line_ids:
            my_qty = sbom.product_qty
            if not sbom.attribute_value_ids:
                # No attribute_value_ids means the bom line is not variant specific
                price += uom_obj._compute_price(cr, uid, sbom.product_id.uom_id.id, sbom.product_id.standard_price, sbom.product_uom.id) * my_qty

        if bom.routing_id:
            for wline in bom.routing_id.workcenter_lines:
                wc = wline.workcenter_id
                cycle = wline.cycle_nbr
                hour = (wc.time_start + wc.time_stop + cycle * wc.time_cycle) *  (wc.time_efficiency or 1.0)
                price += wc.costs_cycle * cycle + wc.costs_hour * hour
                price = self.pool.get('product.uom')._compute_price(cr,uid,bom.product_uom.id, price, bom.product_id.uom_id.id)
        
        #Convert on product UoM quantities
        if price > 0:
            price = uom_obj._compute_price(cr, uid, bom.product_uom.id, price / bom.product_qty, bom.product_id.uom_id.id)

        product = tmpl_obj.browse(cr, uid, bom.product_tmpl_id.id, context=context)
        if not test:
            if (product.valuation != "real_time" or not real_time_accounting):
                tmpl_obj.write(cr, uid, [product.id], {'standard_price' : price}, context=context)
            else:
                #Call wizard function here
                wizard_obj = self.pool.get("stock.change.standard.price")
                ctx = context.copy()
                ctx.update({'active_id': product.id, 'active_model': 'product.template'})
                wiz_id = wizard_obj.create(cr, uid, {'new_price': price}, context=ctx)
                wizard_obj.change_price(cr, uid, [wiz_id], context=ctx)
        return price


class product_bom(osv.osv):
    _inherit = 'mrp.bom'
            
    _columns = {
        'standard_price': fields.related('product_tmpl_id','standard_price',type="float",relation="product.product",string="Standard Price",store=False)
    }

class mrp_production(osv.Model):
    _inherit = 'mrp.production'

    def _get_production_costs(self, cr, uid, mo, context=None):
        total = 0.0
        for consumed_move in mo.move_lines2:
            for consumed_quant in consumed_move.quant_ids:
                total += consumed_quant.inventory_value

        if mo.bom_id.routing_id:
            bom = mo.bom_id
            for wline in bom.routing_id.workcenter_lines:
                wc = wline.workcenter_id
                cycle = wline.cycle_nbr
                hour = (wc.time_start + wc.time_stop + cycle * wc.time_cycle) *  (wc.time_efficiency or 1.0)
                total += wc.costs_cycle * cycle + wc.costs_hour * hour
                total = self.pool.get('product.uom')._compute_price(cr,uid,bom.product_uom.id, total, bom.product_id.uom_id.id)
        return total

    def _update_cost_price(self, cr, uid, ids, context=None):
        """Rectify cost of finished product after production

        This should be done in post-process as original production (action_produce)
        will first generate moves for the finished product and then the components.
        The components are valuated only once consumed so need to rectify the price.
        """
        quant_obj = self.pool['stock.quant']
        for mo in self.browse(cr, uid, ids, context=context):
            if mo.product_id.cost_method == 'standard':
                # cost price is specified on product form
                continue

            total_cost = self._get_production_costs(cr, uid, mo, context=context)
            produced_price_unit = total_cost/mo.product_qty
            for move in mo.move_created_ids2:
                finished_quant_ids = [q.id for q in move.quant_ids if q.cost != produced_price_unit]
                quant_obj.write(cr, uid, finished_quant_ids,
                    {'cost': produced_price_unit}, context=context)

                if move.product_id.valuation == 'real_time':
                    # has generated accounting entries with wrong price
                    # correction of the entry
                    price_difference = produced_price_unit - move.price_unit
                    if produced_price_unit and price_difference:
                        self.pool['stock.move']._rectify_account_entry(cr, uid, move, produced_price_unit, context=context)

            if mo.product_id.cost_method == 'average':
                qty_available = mo.product_id.product_tmpl_id.qty_available
                amount_unit = mo.product_id.standard_price
                # current stock valuation at average price
                current_stock_price = amount_unit * qty_available

                # remove the move with wrong price
                qty_before_mo = qty_available - mo.product_qty
                price_before_mo = (current_stock_price - (mo.move_created_ids2[0].price_unit * mo.product_qty)) / qty_before_mo

                # recompute the new average price with correct price_unit
                new_average_price = ((price_before_mo * qty_before_mo) + (produced_price_unit * mo.product_qty)) / qty_available

                # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
                self.pool['product.product'].write(cr, SUPERUSER_ID, [mo.product_id.id],
                    {'standard_price': new_average_price}, context=context)

            # rectify the price_unit on the move in case of return
            self.pool['stock.move'].write(cr, uid, [m.id for m in mo.move_created_ids2],
                {'price_unit': produced_price_unit}, context=context)

        return True

    def action_production_end(self, cr, uid, ids, context=None):
        """ Changes production state to Finish and writes finished date.
        @return: True
        """
        res = super(mrp_production, self).action_production_end(cr, uid, ids, context=context)
        self._update_cost_price(cr, uid, ids, context=context)
        return res

class stock_move(osv.Model):
    _inherit = 'stock.move'

    def _rectify_account_entry(self, cr, uid, move, produced_price_unit, context=None):
        account_move = self.pool['account.move']
        account_move_line = self.pool['account.move.line']
        stock_quant = self.pool['stock.quant']

        accounts = stock_quant._get_accounting_data_for_entry_move(cr, uid, move.quant_ids, move, context=context)
        if not accounts:
            return False

        credit_account_id, debit_account_id, journal_id, company_id = accounts
        # we don't know which entry was generated by which move
        # doing search, hoping it will be enough
        dummy_matching = account_move.search(cr, uid, [
                ('ref', '=', stock_quant._get_account_move_ref(cr, uid, move, context=context)),
                ('journal_id', '=', journal_id),
            ], context=context)
        if not dummy_matching:
            _logger.warning("No matching stock entries were found, could not correct the valuation")
            return False
        elif len(dummy_matching) > 1:
            dummy_line_matching = account_move_line.search(cr, uid, [
                ('move_id', 'in', dummy_matching),
                ('product_id', '=', move.product_id.id),
                ('quantity', '=', move.product_qty),
                '|',
                    ('debit', '=', move.price_unit*move.product_qty),
                    ('credit', '=', move.price_unit*move.product_qty),
                ], context=context)
            if not dummy_line_matching:
                _logger.warning("Could not match generated entries with the manufactured stock.move, skip correction of the valuation")
                return False

        else:
            dummy_line_matching = [line.id for line in account_move.browse(cr, uid, dummy_matching[0], context=context).line_id]

        for line in account_move_line.browse(cr, uid, dummy_line_matching, context=context):
            if line.credit or (not line.debit and line.account_id.id == credit_account_id):
                account_move_line.write(cr, uid, [line.id], {'credit': produced_price_unit*move.product_qty}, context=context)
            else:
                account_move_line.write(cr, uid, [line.id], {'debit': produced_price_unit*move.product_qty}, context=context)
