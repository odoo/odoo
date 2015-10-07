# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict
from openerp import api, fields, models, _
from openerp.exceptions import AccessError, UserError
from openerp.tools import float_compare, float_is_zero
import openerp.addons.decimal_precision as dp


class MrpProduction(models.Model):
    """
    Production Orders / Manufacturing Orders
    """
    _name = 'mrp.production'
    _description = 'Manufacturing Order'
    _date_name = 'date_planned'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'priority desc, date_planned asc'

    def _src_id_default(self):
        try:
            location_id = self.env.ref('stock.stock_location_stock')
            location_id.check_access_rule('read')
        except (AccessError, ValueError):
            location_id = False
        return location_id

    def _dest_id_default(self):
        try:
            location_id = self.env.ref('stock.stock_location_stock')
            location_id.check_access_rule('read')
        except (AccessError, ValueError):
            location_id = False
        return location_id

    name = fields.Char(string='Reference', required=True, readonly=True, states={'draft': [('readonly', False)]}, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code('mrp.production') or '/')
    origin = fields.Char(string='Source Document', readonly=True, states={'draft': [('readonly', False)]},
        help="Reference of the document that generated this production order request.", copy=False)
    priority = fields.Selection([('0', 'Not urgent'), ('1', 'Normal'), ('2', 'Urgent'), ('3', 'Very Urgent')], 'Priority',
        index=True, readonly=True, states=dict.fromkeys(['draft', 'confirmed'], [('readonly', False)]), default='1')
    product_id = fields.Many2one('product.product', string='Product', required=True, readonly=True, states={'draft': [('readonly', False)]}, domain=[('type','!=','service')])
    product_qty = fields.Float(string='Product Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True, readonly=True, states={'draft': [('readonly', False)]}, default=1.0)
    product_uom_id = fields.Many2one('product.uom', string='Product Unit of Measure', required=True, readonly=True, states={'draft': [('readonly', False)]}, oldname='product_uom')
    progress = fields.Float(compute='_get_progress', string='Production progress')
    location_src_id = fields.Many2one('stock.location', string='Raw Materials Location', required=True,
        readonly=True, states={'draft': [('readonly', False)]}, default=_src_id_default,
        help="Location where the system will look for components.")
    location_dest_id = fields.Many2one('stock.location', string='Finished Products Location', required=True,
        readonly=True, states={'draft': [('readonly', False)]}, default=_dest_id_default,
        help="Location where the system will stock the finished products.")
    date_planned = fields.Datetime(string='Scheduled Date', required=True, index=True, readonly=True, states={'draft': [('readonly', False)]}, copy=False, default=fields.Datetime.now)
    date_start = fields.Datetime(string='Start Date', index=True, readonly=True, copy=False)
    date_finished = fields.Datetime(string='End Date', index=True, readonly=True, copy=False)
    bom_id = fields.Many2one('mrp.bom', string='Bill of Material', readonly=True, states={'draft': [('readonly', False)]},
        help="Bill of Materials allow you to define the list of required raw materials to make a finished product.")
    routing_id = fields.Many2one('mrp.routing', string='Work Order Operations', on_delete='set null', readonly=True, states={'draft': [('readonly', False)]},
        help="The list of operations (list of work centers) to produce the finished product. The routing is mainly used to compute work center costs during operations and to plan future loads on work centers based on production plannification.")
    move_prod_id = fields.Many2one('stock.move', string='Product Move', readonly=True, copy=False)
    move_line_ids = fields.One2many('stock.move', 'raw_material_production_id', string='Products to Consume',
        domain=[('state', 'not in', ('done', 'cancel'))], readonly=True, states={'draft': [('readonly', False)]}, oldname='move_lines')
    move_line_ids2 = fields.One2many('stock.move', 'raw_material_production_id', string='Consumed Products',
        domain=[('state', 'in', ('done', 'cancel'))], readonly=True, oldname='move_lines2')
    move_created_ids = fields.One2many('stock.move', 'production_id', string='Products to Produce',
        domain=[('state', 'not in', ('done', 'cancel'))], readonly=True)
    move_created_ids2 = fields.One2many('stock.move', 'production_id', 'Produced Products',
        domain=[('state', 'in', ('done', 'cancel'))], readonly=True)
    product_line_ids = fields.One2many('mrp.production.product.line', 'production_id', string='Scheduled goods', readonly=True, oldname='product_lines')
    workcenter_line_ids = fields.One2many('mrp.production.workcenter.line', 'production_id', string='Work Centers Utilisation',
        readonly=True, states={'draft': [('readonly', False)]}, oldname='workcenter_lines')
    state = fields.Selection(
        [('draft', 'New'), ('cancel', 'Cancelled'), ('confirmed', 'Awaiting Raw Materials'),
            ('ready', 'Ready to Produce'), ('in_production', 'Production Started'), ('done', 'Done')],
        string='Status', readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help="When the production order is created the status is set to 'Draft'.\n"
            "If the order is confirmed the status is set to 'Waiting Goods.\n"
            "If any exceptions are there, the status is set to 'Picking Exception.\n"
            "If the stock is available then the status is set to 'Ready to Produce.\n"
            "When the production gets started then the status is set to 'In Production.\n"
            "When the production is over, the status is set to 'Done'.")
    hour_total = fields.Float(compute='_production_calc', string='Total Hours', store=True)
    cycle_total = fields.Float(compute='_production_calc', string='Total Cycles', store=True)
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env['res.company']._company_default_get('mrp.production'))
    ready_production = fields.Boolean(compute='_moves_assigned', string="Ready for production", store=True)
    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id', string='Product')
    categ_id = fields.Many2one('product.category', related='product_tmpl_id.categ_id', string='Product Category', readonly=True, store = True)

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per Company!'),
    ]

    @api.multi
    @api.depends('workcenter_line_ids.hour', 'workcenter_line_ids.cycle')
    def _production_calc(self):
        """ Calculates total hours and total no. of cycles for a production order.
        :return: Dictionary of values.
        """
        data = self.env['mrp.production.workcenter.line'].read_group([('production_id', 'in', self.ids)], ['hour', 'cycle', 'production_id'], ['production_id'])
        mapped_data = dict([(m['production_id'][0], {'hour': m['hour'] , 'cycle': m['cycle']}) for m in data])
        for record in self:
            record.hour_total = mapped_data.get(record.id, {}).get('hour', 0)
            record.cycle_total = mapped_data.get(record.id, {}).get('cycle', 0)

    def _get_progress(self):
        """ Return product quantity percentage """
        result = dict.fromkeys(self.ids, 100)
        for mrp_production in self:
            if mrp_production.product_qty:
                done = 0.0
                for move in mrp_production.move_created_ids2:
                    if not move.scrapped and move.product_id == mrp_production.product_id:
                        done += move.product_qty
                result[mrp_production.id] = done / mrp_production.product_qty * 100
        return result

    @api.multi
    @api.depends('move_line_ids.state')
    def _moves_assigned(self):
        """ Test whether all the consume lines are assigned """
        for production in self:
            production.ready_production = True
            states = [record.state != 'assigned' for record in production.move_line_ids if record]
            if any(states) or len(states) == 0:  # When no moves, ready_production will be False, but test_ready will pass
                production.ready_production = False

    @api.constrains('product_qty')
    def _check_qty(self):
        if self.product_qty <= 0:
            raise ValueError(_('Order quantity cannot be negative or zero!'))

    @api.model
    def create(self, values):
        if 'product_id' in values and not 'product_uom_id' in values:
            values['product_uom_id'] = self.env['product.product'].browse(values.get('product_id')).uom_id.id
        return super(MrpProduction, self).create(values)

    @api.multi
    def unlink(self):
        for production in self:
            if production.state not in ('draft', 'cancel'):
                raise UserError(_('Cannot delete a manufacturing order in state \'%s\'.') % production.state)
        return super(MrpProduction, self).unlink()

    @api.onchange('location_src_id')
    def onchange_location_id(self):
        if self.location_dest_id.id:
            return
        if self.location_src_id.id:
            self.location_dest_id = self.location_src_id.id

    @api.multi
    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.product_id:
            self.product_uom_id = False
            self.bom_id = False
            self.routing_id = False
            self.product_tmpl_id = False
        else:
            bom_id = self.env['mrp.bom']._bom_find(product_id=self.product_id.id, properties=[])
            routing_id = False
            if bom_id:
                bom_point = self.env['mrp.bom'].browse(bom_id)
                routing_id = bom_point.routing_id.id or False
            product_uom = self.product_id.uom_id and self.product_id.uom_id.id or False
            self.product_uom_id = product_uom
            self.bom_id = bom_id
            self.routing_id = routing_id
            self.product_tmpl_id = self.product_id.product_tmpl_id

    @api.onchange('bom_id')
    def onchange_bom_id(self):
        if not self.bom_id:
            self.routing_id = False
        self.routing_id = self.bom_id.routing_id.id or False

    @api.model
    def _prepare_lines(self, properties=None):
        # search BoM structure and route
        MrpBom = self.env['mrp.bom']
        bom_point = self.bom_id
        bom_id = self.bom_id.id
        if not bom_point:
            bom_id = MrpBom._bom_find(product_id=self.product_id.id, properties=properties)
            if bom_id:
                bom_point = MrpBom.browse(bom_id)
                routing_id = bom_point.routing_id.id or False
                self.write({'bom_id': bom_id, 'routing_id': routing_id})

        if not bom_id:
            raise UserError(_("Cannot find a bill of material for this product."))

        # get components and workcenter_line_ids from BoM structure
        factor = self.env['product.uom']._compute_qty(self.product_uom_id.id, self.product_qty, bom_point.product_uom_id.id)
        # product_line_ids, workcenter_line_ids
        return bom_point.explode(self.product_id, factor / bom_point.product_qty, properties, routing_id=self.routing_id.id)

    def _action_compute_lines(self, properties=None):
        """ Compute product_line_ids and workcenter_line_ids from BoM structure
        :return: product_line_ids
        """
        if properties is None:
            properties = []
        results = []
        ProductLine = self.env['mrp.production.product.line']
        WorkcenterLine = self.env['mrp.production.workcenter.line']
        for production in self:
            #unlink product_line_ids
            for line in production.product_line_ids:
                ProductLine.browse(line.id).sudo().unlink()
            #unlink workcenter_line_ids
            for line in production.workcenter_line_ids:
                WorkcenterLine.browse(line.id).sudo().unlink()
            res = production._prepare_lines(properties=properties)
            results = res[0] # product_line_ids
            results2 = res[1] # workcenter_line_ids

            # reset product_line_ids in production order
            for line in results:
                line['production_id'] = production.id
                ProductLine.create(line)

            #reset workcenter_line_ids in production order
            for line in results2:
                line['production_id'] = production.id
                WorkcenterLine.create(line)
        return results

    @api.multi
    def action_compute(self, properties=None):
        """ Computes bills of material of a product.
        :param properties: List containing dictionaries of properties.
        :return: No. of products.
        """
        return len(self._action_compute_lines(properties=properties))

    @api.multi
    def action_cancel(self):
        """ Cancels the production order and related stock moves.
        :return: True
        """
        StockMove = self.env['stock.move']
        ProcurementOrder = self.env['procurement.order']
        for production in self:
            if production.move_created_ids:
                for moves in production.move_created_ids:
                    StockMove.browse(moves.id).action_cancel()
            procs = ProcurementOrder.search([('move_dest_id', 'in', [record.id for record in production.move_line_ids])])
            if procs:
                procs.cancel()
            for moves in production.move_line_ids:
                StockMove.browse(moves.id).action_cancel()
        self.state = 'cancel'
        # Put related procurements in exception
        procs = ProcurementOrder.search([('production_id', 'in', [self.id])])
        if procs:
            procs.message_post(body=_('Manufacturing order cancelled.'))
            procs.write({'state': 'exception'})
        return True

    @api.multi
    def action_ready(self):
        """ Changes the production state to Ready and location id of stock move.
        :return: True
        """
        self.write({'state': 'ready'})
        for production in self:
            if not production.move_created_ids:
                self._make_production_produce_line(production)

            if production.move_prod_id and production.move_prod_id.location_id.id != production.location_dest_id.id:
                production.move_prod_id.write({'location_id': production.location_dest_id.id})
        return True

    @api.multi
    def action_production_end(self):
        """ Changes production state to Finish and writes finished date.
        :return: True
        """
        for production in self:
            self._costs_generate(production)
        write_res = self.write({'state': 'done', 'date_finished': fields.datetime.now()})
        # Check related procurements
        procs = self.env["procurement.order"].search([('production_id', 'in', self.ids)])
        self.env["procurement.order"].check(procs)
        return write_res

    def test_production_done(self):
        """ Tests whether production is done or not.
        :return: True or False
        """
        res = True
        for production in self:
            if production.move_line_ids:
                res = False

            if production.move_created_ids:
                res = False
        return res

    @api.model
    def _get_subproduct_factor(self, production_id, move_id=None):
        """ Compute the factor to compute the qty of procucts to produce for the given production_id. By default,
            it's always equal to the quantity encoded in the production order or the production wizard, but if the
            module mrp_subproduct is installed, then we must use the move_id to identify the product to produce
            and its quantity.
        :param production_id: ID of the mrp.order
        :param move_id: ID of the stock move that needs to be produced. Will be used in mrp_subproduct.
        :return: The factor to apply to the quantity that we should produce for the given production order.
        """
        return 1

    @api.model
    def _get_produced_qty(self, production):
        ''' returns the produced quantity of product 'production.product_id' for the given production, in the product UoM
        '''
        produced_qty = 0
        for produced_product in production.move_created_ids2:
            if (produced_product.scrapped) or (produced_product.product_id.id != production.product_id.id):
                continue
            produced_qty += produced_product.product_qty
        return produced_qty

    @api.model
    def _get_consumed_data(self, production):
        ''' returns a dictionary containing for each raw material of the given production, its quantity already consumed (in the raw material UoM)
        '''
        consumed_data = {}
        # Calculate already consumed qtys
        for consumed in production.move_line_ids2:
            if consumed.scrapped:
                continue
            if not consumed_data.get(consumed.product_id.id, False):
                consumed_data[consumed.product_id.id] = 0
            consumed_data[consumed.product_id.id] += consumed.product_qty
        return consumed_data

    @api.model
    def _calculate_qty(self, production, product_qty=0.0):
        """
            Calculates the quantity still needed to produce an extra number of products
            product_qty is in the uom of the product
        """
        ProductUom = self.env['product.uom']
        StockQuant = self.env["stock.quant"]
        produced_qty = self._get_produced_qty(production)
        consumed_data = self._get_consumed_data(production)

        #In case no product_qty is given, take the remaining qty to produce for the given production
        if not product_qty:
            product_qty = ProductUom._compute_qty(production.product_uom_id.id, production.product_qty, production.product_id.uom_id.id) - produced_qty
        production_qty = ProductUom._compute_qty(production.product_uom_id.id, production.product_qty, production.product_id.uom_id.id)

        scheduled_qty = OrderedDict()
        for scheduled in production.product_line_ids:
            if scheduled.product_id.type == 'service':
                continue
            qty = ProductUom._compute_qty(scheduled.product_uom_id.id, scheduled.product_qty, scheduled.product_id.uom_id.id)
            if scheduled_qty.get(scheduled.product_id.id):
                scheduled_qty[scheduled.product_id.id] += qty
            else:
                scheduled_qty[scheduled.product_id.id] = qty
        dicts = OrderedDict()
        # Find product qty to be consumed and consume it
        for product_id in scheduled_qty.keys():

            consumed_qty = consumed_data.get(product_id, 0.0)

            # qty available for consume and produce
            sched_product_qty = scheduled_qty[product_id]
            qty_avail = sched_product_qty - consumed_qty
            if qty_avail <= 0.0:
                # there will be nothing to consume for this raw material
                continue

            if not dicts.get(product_id):
                dicts[product_id] = {}

            # total qty of consumed product we need after this consumption
            if product_qty + produced_qty <= production_qty:
                total_consume = ((product_qty + produced_qty) * sched_product_qty / production_qty)
            else:
                total_consume = sched_product_qty
            qty = total_consume - consumed_qty

            # Search for quants related to this related move
            for move in production.move_line_ids:
                if qty <= 0.0:
                    break
                if move.product_id.id != product_id:
                    continue

                q = min(move.product_qty, qty)
                quants = StockQuant.quants_get_preferred_domain(q, move, domain=[('qty', '>', 0.0)],
                                                     preferred_domain_list=[[('reservation_id', '=', move.id)]])
                for quant, quant_qty in quants:
                    if quant:
                        lot_id = quant.lot_id.id
                        if not product_id in dicts.keys():
                            dicts[product_id] = {lot_id: quant_qty}
                        elif lot_id in dicts[product_id].keys():
                            dicts[product_id][lot_id] += quant_qty
                        else:
                            dicts[product_id][lot_id] = quant_qty
                        qty -= quant_qty
            if float_compare(qty, 0, self.env['decimal.precision'].precision_get('Product Unit of Measure')) == 1:
                if dicts[product_id].get(False):
                    dicts[product_id][False] += qty
                else:
                    dicts[product_id][False] = qty

        consume_lines = []
        for product in dicts.keys():
            for lot, qty in dicts[product].items():
                consume_lines.append({'product_id': product, 'product_qty': qty, 'lot_id': lot})
        return consume_lines

    @api.model
    def action_produce(self, production_id, production_qty, production_mode, wizard=False):
        """ To produce final product based on production mode (consume/consume&produce).
        If Production mode is consume, all stock move lines of raw materials will be done/consumed.
        If Production mode is consume & produce, all stock move lines of raw materials will be done/consumed
        and stock move lines of final product will be also done/produced.
        :param production_id: the ID of mrp.production object
        :param production_qty: specify qty to produce in the uom of the production order
        :param production_mode: specify production mode (consume/consume&produce).
        :param wizard: the mrp produce product wizard, which will tell the amount of consumed products needed
        :return: True
        """
        StockMove = self.env['stock.move']
        ProductProduct = self.env['product.product']
        production = self.browse(production_id)
        production_qty_uom = self.env["product.uom"]._compute_qty(production.product_uom_id.id, production_qty, production.product_id.uom_id.id)
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        main_production_move = False
        if production_mode == 'consume_produce':
            # To produce remaining qty of final product
            produced_products = {}
            for produced_product in production.move_created_ids2:
                if produced_product.scrapped:
                    continue
                if not produced_products.get(produced_product.product_id.id, False):
                    produced_products[produced_product.product_id.id] = 0
                produced_products[produced_product.product_id.id] += produced_product.product_qty
            for produce_product in production.move_created_ids:
                subproduct_factor = self._get_subproduct_factor(production.id, produce_product.id)
                lot_id = False
                if wizard:
                    lot_id = wizard.lot_id.id
                qty = min(subproduct_factor * production_qty_uom, produce_product.product_qty) #Needed when producing more than maximum quantity
                new_moves = produce_product.action_consume(qty, location_id=produce_product.location_id.id, restrict_lot_id=lot_id)
                produce_product.browse(new_moves).write({'production_id': production_id})
                remaining_qty = subproduct_factor * production_qty_uom - qty
                if not float_is_zero(remaining_qty, precision_digits=precision):
                    # In case you need to make more than planned
                    #consumed more in wizard than previously planned
                    extra_move_id = produce_product.copy(default={'product_uom_qty': remaining_qty, 'production_id': production_id})
                    extra_move_id.action_confirm()
                    extra_move_id.action_done()

                if produce_product.product_id.id == production.product_id.id:
                    main_production_move = produce_product.id

        if production_mode in ['consume', 'consume_produce']:
            if wizard:
                consume_lines = []
                for cons in wizard.consume_lines:
                    consume_lines.append({'product_id': cons.product_id.id, 'lot_id': cons.lot_id.id, 'product_qty': cons.product_qty})
            else:
                consume_lines = self._calculate_qty(production, production_qty_uom)
            for consume in consume_lines:
                remaining_qty = consume['product_qty']
                for raw_material_line in production.move_line_ids:
                    if raw_material_line.state in ('done', 'cancel'):
                        continue
                    if remaining_qty <= 0:
                        break
                    if consume['product_id'] != raw_material_line.product_id.id:
                        continue
                    consumed_qty = min(remaining_qty, raw_material_line.product_qty)
                    raw_material_line.action_consume(consumed_qty, raw_material_line.location_id.id,
                                                 restrict_lot_id=consume['lot_id'], consumed_for_id=main_production_move)
                    remaining_qty -= consumed_qty
                if not float_is_zero(remaining_qty, precision_digits=precision):
                    #consumed more in wizard than previously planned
                    product = ProductProduct.browse(consume['product_id'])
                    extra_move_id = self._make_consume_line_from_data(production, product, product.uom_id.id, remaining_qty, False, 0)
                    extra_move_id.write({'restrict_lot_id': consume['lot_id'], 'consumed_for_id': main_production_move})
                    extra_move_id.action_done()

        production.message_post(body=_("%s produced") % self._description)

        # Remove remaining products to consume if no more products to produce
        if not production.move_created_ids and production.move_line_ids:
            StockMove.action_cancel([x.id for x in production.move_line_ids])

        production.signal_workflow('button_produce_done')
        return True

    @api.model
    def _costs_generate(self, production):
        """ Calculates total costs at the end of the production.
        :param production: Id of production order.
        :return: Calculated amount.
        """
        AccountAnalyticLine = self.env['account.analytic.line']
        amount = 0.0
        for wc_line in production.workcenter_line_ids:
            wc = wc_line.workcenter_id
            if wc.costs_general_account_id:
                # Cost per hour
                value = wc_line.hour * wc.costs_hour
                account = wc.costs_hour_account_id.id
                if value and account:
                    amount += value
                    # we user SUPERUSER_ID as we do not garantee an mrp user
                    # has access to account analytic lines but still should be
                    # able to produce orders
                    AccountAnalyticLine.sudo().create({
                        'name': wc_line.name + ' (H)',
                        'amount': value,
                        'account_id': account,
                        'general_account_id': wc.costs_general_account_id.id,
                        'ref': wc.code,
                        'product_id': wc.product_id.id,
                        'unit_amount': wc_line.hour,
                        'product_uom_id': wc.product_id and wc.product_id.uom_id.id or False
                    })
                # Cost per cycle
                value = wc_line.cycle * wc.costs_cycle
                account = wc.costs_cycle_account_id.id
                if value and account:
                    amount += value
                    AccountAnalyticLine.sudo().create({
                        'name': wc_line.name + ' (C)',
                        'amount': value,
                        'account_id': account,
                        'general_account_id': wc.costs_general_account_id.id,
                        'ref': wc.code,
                        'product_id': wc.product_id.id,
                        'unit_amount': wc_line.cycle,
                        'product_uom_id': wc.product_id and wc.product_id.uom_id.id or False
                    })
        return amount

    @api.multi
    def action_in_production(self):
        """ Changes state to In Production and writes starting date.
        :return: True
        """
        return self.write({'state': 'in_production', 'date_start': fields.Datetime.now()})

    def consume_lines_get(self):
        res = []
        for order in self:
            res += [x.id for x in order.move_line_ids]
        return res

    @api.multi
    def test_ready(self):
        res = True
        for production in self:
            if production.move_line_ids and not production.ready_production:
                res = False
        return res

    @api.model
    def _make_production_produce_line(self, production):
        source_location_id = production.product_id.property_stock_production.id
        destination_location_id = production.location_dest_id.id
        procs = self.env['procurement.order'].search([('production_id', '=', production.id)]).ids
        procurement = procs and self.env['procurement.order'].browse(procs[0])
        data = {
            'name': production.name,
            'date': production.date_planned,
            'product_id': production.product_id.id,
            'product_uom': production.product_uom_id.id,
            'product_uom_qty': production.product_qty,
            'location_id': source_location_id,
            'location_dest_id': destination_location_id,
            'move_dest_id': production.move_prod_id.id,
            'procurement_id': procurement and procurement.id,
            'company_id': production.company_id.id,
            'production_id': production.id,
            'origin': production.name,
            'group_id': procurement and procurement.group_id.id,
        }
        move_id = self.env['stock.move'].create(data)
        #a phantom bom cannot be used in mrp order so it's ok to assume the list returned by action_confirm
        #is 1 element long, so we can take the first.
        return move_id.action_confirm()[0]

    @api.model
    def _get_raw_material_procure_method(self, product, location_id=False, location_dest_id=False):
        '''This method returns the procure_method to use when creating the stock move for the production raw materials
        Besides the standard configuration of looking if the product or product category has the MTO route,
        you can also define a rule e.g. from Stock to Production (which might be used in the future like the sale orders)
        '''
        routes = product.route_ids + product.categ_id.total_route_ids

        if location_id and location_dest_id:
            pulls = self.env['procurement.rule'].search([('route_id', 'in', [x.id for x in routes]),
                                            ('location_id', '=', location_dest_id),
                                            ('location_src_id', '=', location_id)], limit=1)
            if pulls:
                return self.env['procurement.rule'].browse(pulls[0]).procure_method

        try:
            mto_route = self.env['stock.warehouse']._get_mto_route()
        except:
            return "make_to_stock"

        if mto_route in [x.id for x in routes]:
            return "make_to_order"
        return "make_to_stock"

    @api.model
    def _create_previous_move(self, move_id, product, source_location_id, dest_location_id):
        '''
        When the routing gives a different location than the raw material location of the production order, 
        we should create an extra move from the raw material location to the location of the routing, which 
        precedes the consumption line (chained).  The picking type depends on the warehouse in which this happens
        and the type of locations. 
        '''
        StockLocation = self.env["stock.location"]
        StockMove = self.env['stock.move']
        # Need to search for a picking type
        move = StockMove.browse(move_id)
        src_loc = StockLocation.browse(source_location_id)
        dest_loc = StockLocation.browse(dest_location_id)
        code = StockMove.get_code_from_locs(move, src_loc, dest_loc)
        if code == 'outgoing':
            check_loc = src_loc
        else:
            check_loc = dest_loc
        warehouse = StockLocation.get_warehouse(check_loc)
        domain = [('code', '=', code)]
        if warehouse:
            domain += [('warehouse_id', '=', warehouse)]
        types = self.env['stock.picking.type'].search(domain)
        move = StockMove.copy(move_id, default={
            'location_id': source_location_id,
            'location_dest_id': dest_location_id,
            'procure_method': self._get_raw_material_procure_method(product, location_id=source_location_id,
                                                                    location_dest_id=dest_location_id),
            'raw_material_production_id': False,
            'move_dest_id': move_id,
            'picking_type_id': types and types[0] or False,
        })
        return move

    @api.model
    def _make_consume_line_from_data(self, production, product, uom_id, qty):
        # Internal shipment is created for Stockable and Consumer Products
        if product.type not in ('product', 'consu'):
            return False
        # Take routing location as a Source Location.
        source_location_id = production.location_src_id.id
        prod_location_id = source_location_id
        prev_move= False
        if production.bom_id.routing_id and production.bom_id.routing_id.location_id and production.bom_id.routing_id.location_id.id != source_location_id:
            source_location_id = production.bom_id.routing_id.location_id.id
            prev_move = True

        destination_location_id = production.product_id.property_stock_production.id
        move_id = self.env['stock.move'].create({
            'name': production.name,
            'date': production.date_planned,
            'product_id': product.id,
            'product_uom_qty': qty,
            'product_uom': uom_id,
            'location_id': source_location_id,
            'location_dest_id': destination_location_id,
            'company_id': production.company_id.id,
            'procure_method': prev_move and 'make_to_stock' or self._get_raw_material_procure_method(product, location_id=source_location_id,
                                                                                                     location_dest_id=destination_location_id), #Make_to_stock avoids creating procurement
            'raw_material_production_id': production.id,
            #this saves us a browse in create()
            'price_unit': product.standard_price,
            'origin': production.name,
            'warehouse_id': self.env['stock.location'].get_warehouse(production.location_src_id),
            'group_id': production.move_prod_id.group_id.id
        })

        if prev_move:
            prev_move = self._create_previous_move(move_id, product, prod_location_id, source_location_id)
            self.env['stock.move'].browse(prev_move).action_confirm()
        return move_id

    @api.model
    def _make_production_consume_line(self, line):
        return self._make_consume_line_from_data(line.production_id, line.product_id, line.product_uom_id.id, line.product_qty)

    @api.model
    def _make_service_procurement(self, line):
        if self.env['product.product'].need_procurement():
            vals = {
                'name': line.production_id.name,
                'origin': line.production_id.name,
                'company_id': line.production_id.company_id.id,
                'date_planned': line.production_id.date_planned,
                'product_id': line.product_id.id,
                'product_qty': line.product_qty,
                'product_uom_id': line.product_uom_id.id,
            }
            ProcurementOrder = self.env["procurement.order"]
            procurement = ProcurementOrder.create(vals)
            ProcurementOrder.run([procurement])

    @api.multi
    def action_confirm(self):
        """ Confirms production order.
        :return: Newly generated Shipment Id.
        """
        user_lang = self.env['res.users'].browse([self.env.uid]).partner_id.lang
        uncompute_ids = filter(lambda x: x, [not x.product_line_ids and x.id or False for x in self])
        self.browse(uncompute_ids).with_context(dict(lang=user_lang)).action_compute()
        for production in self:
            self._make_production_produce_line(production)

            stock_moves = []
            for line in production.product_line_ids:
                if line.product_id.type != 'service':
                    stock_move_id = self._make_production_consume_line(line)
                    stock_moves.append(stock_move_id)
                else:
                    self._make_service_procurement(line)
            if stock_moves:
                for move in stock_moves:
                    move.action_confirm()
            production.write({'state': 'confirmed'})
        return 0

    @api.multi
    def action_assign(self):
        """
        Checks the availability on the consume lines of the production order
        """
        StockMove = self.env['stock.move']
        MrpProduction = self.env['mrp.production']
        from openerp import workflow
        for production in self:
            for move in production.move_line_ids:
                StockMove.browse(move.id).action_assign()
            if MrpProduction.browse(production.id).test_ready():
                workflow.trg_validate(self.env.uid, 'mrp.production', production.id, 'moves_ready', self.env.cr)

    @api.multi
    def force_production(self):
        StockMove = self.env['stock.move']
        MrpProduction = self.env['mrp.production']
        from openerp import workflow
        for order in self:
            for move in order.move_line_ids:
                StockMove.browse(move.id).force_assign()
            if MrpProduction.browse(order.id).test_ready():
                workflow.trg_validate(self.env.uid, 'mrp.production', order.id, 'moves_ready', self.env.cr)
        return True


class MrpProductionWorkcenterLine(models.Model):
    _name = 'mrp.production.workcenter.line'
    _description = 'Work Order'
    _order = 'sequence'
    _inherit = ['mail.thread']

    name = fields.Char(string='Work Order', required=True)
    workcenter_id = fields.Many2one('mrp.workcenter', string='Work Center', required=True)
    cycle = fields.Float(string='Number of Cycles', digits=(16, 2))
    hour = fields.Float(string='Number of Hours', digits=(16, 2))
    sequence = fields.Integer(string='Sequence', required=True, default=1, help="Gives the sequence order when displaying a list of work orders.")
    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', track_visibility='onchange', index=True, ondelete='cascade', required=True)


class MrpProductionProductLine(models.Model):
    _name = 'mrp.production.product.line'
    _description = 'Production Scheduled Product'

    name = fields.Char(required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_qty = fields.Float(string='Product Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True)
    product_uom_id = fields.Many2one('product.uom', string='Product Unit of Measure', required=True, oldname='product_uom')
    production_id = fields.Many2one('mrp.production', string='Production Order', index=True)
