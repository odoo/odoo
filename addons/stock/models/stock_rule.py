# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import namedtuple, OrderedDict, defaultdict
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import split_every
from psycopg2 import OperationalError

from odoo import api, fields, models, registry, SUPERUSER_ID, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare, float_round

from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class StockRule(models.Model):
    """ A rule describe what a procurement should do; produce, buy, move, ... """
    _name = 'stock.rule'
    _description = "Stock Rule"
    _order = "sequence, id"

    name = fields.Char(
        'Name', required=True, translate=True,
        help="This field will fill the packing origin and the name of its moves")
    active = fields.Boolean(
        'Active', default=True,
        help="If unchecked, it will allow you to hide the rule without removing it.")
    group_propagation_option = fields.Selection([
        ('none', 'Leave Empty'),
        ('propagate', 'Propagate'),
        ('fixed', 'Fixed')], string="Propagation of Procurement Group", default='propagate')
    group_id = fields.Many2one('procurement.group', 'Fixed Procurement Group')
    action = fields.Selection(
        selection=[('pull', 'Pull From'), ('push', 'Push To'), ('pull_push', 'Pull & Push')], string='Action',
        required=True)
    sequence = fields.Integer('Sequence', default=20)
    company_id = fields.Many2one('res.company', 'Company',
        default=lambda self: self.env.user.company_id)
    location_id = fields.Many2one('stock.location', 'Destination Location', required=True)
    location_src_id = fields.Many2one('stock.location', 'Source Location')
    route_id = fields.Many2one('stock.location.route', 'Route', required=True, ondelete='cascade')
    procure_method = fields.Selection([
        ('make_to_stock', 'Take From Stock'),
        ('make_to_order', 'Trigger Another Rule'),
        ('mts_else_mto', 'Take From Stock, if unavailable, Trigger Another Rule')], string='Move Supply Method',
        default='make_to_stock', required=True,
        help="Take From Stock: the products will be taken from the available stock of the source location.\n"
             "Trigger Another Rule: the system will try to find a stock rule to bring the products in the source location. The available stock will be ignored.\n"
             "Take From Stock, if Unavailable, Trigger Another Rule: the products will be taken from the available stock of the source location."
             "If there is no stock available, the system will try to find a  rule to bring the products in the source location.")
    route_sequence = fields.Integer('Route Sequence', related='route_id.sequence', store=True, readonly=False)
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        required=True)
    delay = fields.Integer('Delay', default=0, help="The expected date of the created transfer will be computed based on this delay.")
    partner_address_id = fields.Many2one('res.partner', 'Partner Address', help="Address where goods should be delivered. Optional.")
    propagate = fields.Boolean(
        'Propagate cancel and split', default=True,
        help="When ticked, if the move is splitted or cancelled, the next move will be too.")
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    propagate_warehouse_id = fields.Many2one(
        'stock.warehouse', 'Warehouse to Propagate',
        help="The warehouse to propagate on the created move/procurement, which can be different of the warehouse this rule is for (e.g for resupplying rules from another warehouse)")
    auto = fields.Selection([
        ('manual', 'Manual Operation'),
        ('transparent', 'Automatic No Step Added')], string='Automatic Move',
        default='manual', index=True, required=True,
        help="The 'Manual Operation' value will create a stock move after the current one. "
             "With 'Automatic No Step Added', the location is replaced in the original move.")
    rule_message = fields.Html(compute='_compute_action_message')

    @api.onchange('picking_type_id')
    def _onchange_picking_type(self):
        """ Modify locations to the default picking type's locations source and
        destination.
        """
        self.location_src_id = self.picking_type_id.default_location_src_id.id
        self.location_id = self.picking_type_id.default_location_dest_id.id

    @api.onchange('route_id', 'company_id')
    def _onchange_route(self):
        """ Ensure that the rule's company is the same than the route's company. """
        if self.route_id.company_id:
            self.company_id = self.route_id.company_id
        if self.picking_type_id.warehouse_id.company_id != self.route_id.company_id:
            self.picking_type_id = False
        domain = {'company_id': self.route_id.company_id and [('id', '=', self.route_id.company_id.id)] or []}
        return {'domain': domain}

    def _get_message_values(self):
        """ Return the source, destination and picking_type applied on a stock
        rule. The purpose of this function is to avoid code duplication in
        _get_message_dict functions since it often requires those data.
        """
        source = self.location_src_id and self.location_src_id.display_name or _('Source Location')
        destination = self.location_id and self.location_id.display_name or _('Destination Location')
        operation = self.picking_type_id and self.picking_type_id.name or _('Operation Type')
        return source, destination, operation

    def _get_message_dict(self):
        """ Return a dict with the different possible message used for the
        rule message. It should return one message for each stock.rule action
        (except push and pull). This function is override in mrp and
        purchase_stock in order to complete the dictionary.
        """
        message_dict = {}
        source, destination, operation = self._get_message_values()
        if self.action in ('push', 'pull', 'pull_push'):
            suffix = ""
            if self.procure_method == 'make_to_order' and self.location_src_id:
                suffix = _("<br>A need is created in <b>%s</b> and a rule will be triggered to fulfill it.") % (source)
            if self.procure_method == 'mts_else_mto' and self.location_src_id:
                suffix = _("<br>If the products are not available in <b>%s</b>, a rule will be triggered to bring products in this location.") % source
            message_dict = {
                'pull': _('When products are needed in <b>%s</b>, <br/> <b>%s</b> are created from <b>%s</b> to fulfill the need.') % (destination, operation, source) + suffix,
                'push': _('When products arrive in <b>%s</b>, <br/> <b>%s</b> are created to send them in <b>%s</b>.') % (source, operation, destination)
            }
        return message_dict

    @api.depends('action', 'location_id', 'location_src_id', 'picking_type_id', 'procure_method')
    def _compute_action_message(self):
        """ Generate dynamicaly a message that describe the rule purpose to the
        end user.
        """
        for rule in self.filtered(lambda rule: rule.action):
            message_dict = rule._get_message_dict()
            message = message_dict.get(rule.action) and message_dict[rule.action] or ""
            if rule.action == 'pull_push':
                message = message_dict['pull'] + "<br/><br/>" + message_dict['push']
            rule.rule_message = message

    def _run_push(self, move):
        """ Apply a push rule on a move.
        If the rule is 'no step added' it will modify the destination location
        on the move.
        If the rule is 'manual operation' it will generate a new move in order
        to complete the section define by the rule.
        Care this function is not call by method run. It is called explicitely
        in stock_move.py inside the method _push_apply
        """
        new_date = fields.Datetime.to_string(move.date_expected + relativedelta(days=self.delay))
        if self.auto == 'transparent':
            move.write({
                'date': new_date,
                'date_expected': new_date,
                'location_dest_id': self.location_id.id})
            # avoid looping if a push rule is not well configured; otherwise call again push_apply to see if a next step is defined
            if self.location_id != move.location_dest_id:
                # TDE FIXME: should probably be done in the move model IMO
                move._push_apply()
        else:
            new_move_vals = self._push_prepare_move_copy_values(move, new_date)
            new_move = move.copy(new_move_vals)
            move.write({'move_dest_ids': [(4, new_move.id)]})
            new_move._action_confirm()

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        new_move_vals = {
            'origin': move_to_copy.origin or move_to_copy.picking_id.name or "/",
            'location_id': move_to_copy.location_dest_id.id,
            'location_dest_id': self.location_id.id,
            'date': new_date,
            'date_expected': new_date,
            'company_id': self.company_id.id,
            'picking_id': False,
            'picking_type_id': self.picking_type_id.id,
            'propagate': self.propagate,
            'warehouse_id': self.warehouse_id.id,
        }
        return new_move_vals

    @api.model
    def _run_pull(self, procurements):
        moves_values_by_company = defaultdict(list)
        mtso_products_by_locations = defaultdict(list)

        # To handle the `mts_else_mto` procure method, we do a preliminary loop to
        # isolate the products we would need to read the forecasted quantity,
        # in order to to batch the read. We also make a sanitary check on the
        # `location_src_id` field.
        for procurement, rule in procurements:
            if not rule.location_src_id:
                msg = _('No source location defined on stock rule: %s!') % (rule.name, )
                raise UserError(msg)

            if rule.procure_method == 'mts_else_mto':
                mtso_products_by_locations[rule.location_src_id].append(procurement.product_id.id)

        # Get the forecasted quantity for the `mts_else_mto` procurement.
        forecasted_qties_by_loc = {}
        for location, product_ids in mtso_products_by_locations.items():
            products = self.env['product.product'].browse(product_ids).with_context(location=location.id)
            forecasted_qties_by_loc[location] = {product.id: product.virtual_available for product in products}

        # Prepare the move values, adapt the `procure_method` if needed.
        for procurement, rule in procurements:
            procure_method = rule.procure_method
            if rule.procure_method == 'mts_else_mto':
                qty_needed = procurement.product_uom._compute_quantity(procurement.product_qty, procurement.product_id.uom_id)
                qty_available = forecasted_qties_by_loc[rule.location_src_id][procurement.product_id.id]
                if float_compare(qty_needed, qty_available, precision_rounding=procurement.product_id.uom_id.rounding) <= 0:
                    procure_method = 'make_to_stock'
                    forecasted_qties_by_loc[rule.location_src_id][procurement.product_id.id] -= qty_needed
                else:
                    procure_method = 'make_to_order'

            move_values = rule._get_stock_move_values(*procurement)
            move_values['procure_method'] = procure_method
            moves_values_by_company[procurement.company_id.id].append(move_values)

        for company_id, moves_values in moves_values_by_company.items():
            # create the move as SUPERUSER because the current user may not have the rights to do it (mto product launched by a sale for example)
            moves = self.env['stock.move'].sudo().with_context(force_company=company_id).create(moves_values)
            # Since action_confirm launch following procurement_group we should activate it.
            moves._action_confirm()
        return True

    def _get_custom_move_fields(self):
        """ The purpose of this method is to be override in order to easily add
        fields from procurement 'values' argument to move data.
        """
        return []

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        ''' Returns a dictionary of values that will be used to create a stock move from a procurement.
        This function assumes that the given procurement has a rule (action == 'pull' or 'pull_push') set on it.

        :param procurement: browse record
        :rtype: dictionary
        '''
        group_id = False
        if self.group_propagation_option == 'propagate':
            group_id = values.get('group_id', False) and values['group_id'].id
        elif self.group_propagation_option == 'fixed':
            group_id = self.group_id.id

        date_expected = fields.Datetime.to_string(
            fields.Datetime.from_string(values['date_planned']) - relativedelta(days=self.delay or 0)
        )
        # it is possible that we've already got some move done, so check for the done qty and create
        # a new move with the correct qty
        qty_left = product_qty
        move_values = {
            'name': name[:2000],
            'company_id': self.company_id.id or self.location_src_id.company_id.id or self.location_id.company_id.id or company_id.id,
            'product_id': product_id.id,
            'product_uom': product_uom.id,
            'product_uom_qty': qty_left,
            'partner_id': self.partner_address_id.id or (values.get('group_id', False) and values['group_id'].partner_id.id) or False,
            'location_id': self.location_src_id.id,
            'location_dest_id': location_id.id,
            'move_dest_ids': values.get('move_dest_ids', False) and [(4, x.id) for x in values['move_dest_ids']] or [],
            'rule_id': self.id,
            'procure_method': self.procure_method,
            'origin': origin,
            'picking_type_id': self.picking_type_id.id,
            'group_id': group_id,
            'route_ids': [(4, route.id) for route in values.get('route_ids', [])],
            'warehouse_id': self.propagate_warehouse_id.id or self.warehouse_id.id,
            'date': date_expected,
            'date_expected': date_expected,
            'propagate': self.propagate,
            'description_picking': product_id._get_description(self.picking_type_id),
            'priority': values.get('priority', "1"),
        }
        for field in self._get_custom_move_fields():
            if field in values:
                move_values[field] = values.get(field)
        return move_values

    def _log_next_activity(self, product_id, note):
        existing_activity = self.env['mail.activity'].search([('res_id', '=',  product_id.product_tmpl_id.id), ('res_model_id', '=', self.env.ref('product.model_product_template').id),
                                                              ('note', '=', note)])
        if not existing_activity:
            # If the user deleted todo activity type.
            try:
                activity_type_id = self.env.ref('mail.mail_activity_data_todo').id
            except:
                activity_type_id = False
            self.env['mail.activity'].create({
                'activity_type_id': activity_type_id,
                'note': note,
                'user_id': product_id.responsible_id.id or SUPERUSER_ID,
                'res_id': product_id.product_tmpl_id.id,
                'res_model_id': self.env.ref('product.model_product_template').id,
            })


class ProcurementGroup(models.Model):
    """
    The procurement group class is used to group products together
    when computing procurements. (tasks, physical products, ...)

    The goal is that when you have one sales order of several products
    and the products are pulled from the same or several location(s), to keep
    having the moves grouped into pickings that represent the sales order.

    Used in: sales order (to group delivery order lines like the so), pull/push
    rules (to pack like the delivery order), on orderpoints (e.g. for wave picking
    all the similar products together).

    Grouping is made only if the source and the destination is the same.
    Suppose you have 4 lines on a picking from Output where 2 lines will need
    to come from Input (crossdock) and 2 lines coming from Stock -> Output As
    the four will have the same group ids from the SO, the move from input will
    have a stock.picking with 2 grouped lines and the move from stock will have
    2 grouped lines also.

    The name is usually the name of the original document (sales order) or a
    sequence computed if created manually.
    """
    _name = 'procurement.group'
    _description = 'Procurement Group'
    _order = "id desc"

    Procurement = namedtuple('Procurement', ['product_id', 'product_qty',
        'product_uom', 'location_id', 'name', 'origin', 'company_id', 'values'])
    partner_id = fields.Many2one('res.partner', 'Partner')
    name = fields.Char(
        'Reference',
        default=lambda self: self.env['ir.sequence'].next_by_code('procurement.group') or '',
        required=True)
    move_type = fields.Selection([
        ('direct', 'Partial'),
        ('one', 'All at once')], string='Delivery Type', default='direct',
        required=True)

    @api.model
    def run(self, procurements):
        """ Method used in a procurement case. The purpose is to supply the
        product passed as argument in the location also given as an argument.
        In order to be able to find a suitable location that provide the product
        it will search among stock.rule.
        """
        actions_to_run = defaultdict(list)
        errors = []
        for procurement in procurements:
            procurement.values.setdefault('company_id', self.env['res.company']._company_default_get('procurement.group'))
            procurement.values.setdefault('priority', '1')
            procurement.values.setdefault('date_planned', fields.Datetime.now())
            rule = self._get_rule(procurement.product_id, procurement.location_id, procurement.values)
            if not rule:
                errors.append(_('No procurement rule found in location "%s" for product "%s".\n Check routes configuration.') %
                    (procurement.location_id.display_name, procurement.product_id.display_name))
            else:
                action = 'pull' if rule.action == 'pull_push' else rule.action
                actions_to_run[action].append((procurement, rule))

        if errors:
            raise UserError('\n'.join(errors))

        for action, procurements in actions_to_run.items():
            if hasattr(self.env['stock.rule'], '_run_%s' % action):
                try:
                    getattr(self.env['stock.rule'], '_run_%s' % action)(procurements)
                except UserError as e:
                    errors.append(e.name)
            else:
                _logger.error("The method _run_%s doesn't exist on the procurement rules" % action)

        if errors:
            raise UserError('\n'.join(errors))
        return True

    @api.model
    def _search_rule(self, route_ids, product_id, warehouse_id, domain):
        """ First find a rule among the ones defined on the procurement
        group, then try on the routes defined for the product, finally fallback
        on the default behavior
        """
        if warehouse_id:
            domain = expression.AND([['|', ('warehouse_id', '=', warehouse_id.id), ('warehouse_id', '=', False)], domain])
        Rule = self.env['stock.rule']
        res = self.env['stock.rule']
        if route_ids:
            res = Rule.search(expression.AND([[('route_id', 'in', route_ids.ids)], domain]), order='route_sequence, sequence', limit=1)
        if not res:
            product_routes = product_id.route_ids | product_id.categ_id.total_route_ids
            if product_routes:
                res = Rule.search(expression.AND([[('route_id', 'in', product_routes.ids)], domain]), order='route_sequence, sequence', limit=1)
        if not res and warehouse_id:
            warehouse_routes = warehouse_id.route_ids
            if warehouse_routes:
                res = Rule.search(expression.AND([[('route_id', 'in', warehouse_routes.ids)], domain]), order='route_sequence, sequence', limit=1)
        return res

    @api.model
    def _get_rule(self, product_id, location_id, values):
        """ Find a pull rule for the location_id, fallback on the parent
        locations if it could not be found.
        """
        result = False
        location = location_id
        while (not result) and location:
            result = self._search_rule(values.get('route_ids', False), product_id, values.get('warehouse_id', False), [('location_id', '=', location.id), ('action', '!=', 'push')])
            location = location.location_id
        return result

    def _merge_domain(self, values, rule, group_id):
        return [
            ('group_id', '=', group_id), # extra logic?
            ('location_id', '=', rule.location_src_id.id),
            ('location_dest_id', '=', values['location_id'].id),
            ('picking_type_id', '=', rule.picking_type_id.id),
            ('picking_id.printed', '=', False),
            ('picking_id.state', 'in', ['draft', 'confirmed', 'waiting', 'assigned']),
            ('picking_id.backorder_id', '=', False),
            ('product_id', '=', values['product_id'].id)]

    @api.model
    def _run_scheduler_tasks(self, use_new_cursor=False, company_id=False):
        # Minimum stock rules
        self.sudo()._procure_orderpoint_confirm(use_new_cursor=use_new_cursor, company_id=company_id)

        # Search all confirmed stock_moves and try to assign them
        moves_to_assign = self.env['stock.move'].search([
            ('state', 'in', ['confirmed', 'partially_available']), ('product_uom_qty', '!=', 0.0)
        ], limit=None, order='priority desc, date_expected asc')
        for moves_chunk in split_every(100, moves_to_assign.ids):
            self.env['stock.move'].browse(moves_chunk)._action_assign()
            if use_new_cursor:
                self._cr.commit()

        if use_new_cursor:
            self._cr.commit()

        # Merge duplicated quants
        self.env['stock.quant']._quant_tasks()

    @api.model
    def run_scheduler(self, use_new_cursor=False, company_id=False):
        """ Call the scheduler in order to check the running procurements (super method), to check the minimum stock rules
        and the availability of moves. This function is intended to be run for all the companies at the same time, so
        we run functions as SUPERUSER to avoid intercompanies and access rights issues. """
        try:
            if use_new_cursor:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))  # TDE FIXME

            self._run_scheduler_tasks(use_new_cursor=use_new_cursor, company_id=company_id)
        finally:
            if use_new_cursor:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return {}

    @api.model
    def _procurement_from_orderpoint_get_order(self):
        return 'location_id'

    @api.model
    def _procurement_from_orderpoint_get_grouping_key(self, orderpoint_ids):
        orderpoints = self.env['stock.warehouse.orderpoint'].browse(orderpoint_ids)
        return orderpoints.location_id.id

    @api.model
    def _procurement_from_orderpoint_get_groups(self, orderpoint_ids):
        """ Make groups for a given orderpoint; by default schedule all operations in one without date """
        return [{'to_date': False, 'procurement_values': dict()}]

    @api.model
    def _procurement_from_orderpoint_post_process(self, orderpoint_ids):
        return True

    def _get_orderpoint_domain(self, company_id=False):
        domain = [('company_id', '=', company_id)] if company_id else []
        domain += [('product_id.active', '=', True)]
        return domain

    @api.model
    def _procure_orderpoint_confirm(self, use_new_cursor=False, company_id=False):
        """ Create procurements based on orderpoints.
        :param bool use_new_cursor: if set, use a dedicated cursor and auto-commit after processing
            1000 orderpoints.
            This is appropriate for batch jobs only.
        """
        if company_id and self.env.user.company_id.id != company_id:
            # To ensure that the company_id is taken into account for
            # all the processes triggered by this method
            # i.e. If a PO is generated by the run of the procurements the
            # sequence to use is the one for the specified company not the
            # one of the user's company
            self = self.with_context(company_id=company_id, force_company=company_id)
        OrderPoint = self.env['stock.warehouse.orderpoint']
        domain = self._get_orderpoint_domain(company_id=company_id)
        orderpoints_noprefetch = OrderPoint.with_context(prefetch_fields=False).search(domain,
            order=self._procurement_from_orderpoint_get_order()).ids
        while orderpoints_noprefetch:
            if use_new_cursor:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))
            OrderPoint = self.env['stock.warehouse.orderpoint']

            orderpoints = OrderPoint.browse(orderpoints_noprefetch[:1000])
            orderpoints_noprefetch = orderpoints_noprefetch[1000:]

            # Calculate groups that can be executed together
            location_data = OrderedDict()

            def makedefault():
                return {
                    'products': self.env['product.product'],
                    'orderpoints': self.env['stock.warehouse.orderpoint'],
                    'groups': []
                }

            for orderpoint in orderpoints:
                key = self._procurement_from_orderpoint_get_grouping_key([orderpoint.id])
                if not location_data.get(key):
                    location_data[key] = makedefault()
                location_data[key]['products'] += orderpoint.product_id
                location_data[key]['orderpoints'] += orderpoint
                location_data[key]['groups'] = self._procurement_from_orderpoint_get_groups([orderpoint.id])

            for location_id, location_data in location_data.items():
                location_orderpoints = location_data['orderpoints']
                product_context = dict(self._context, location=location_orderpoints[0].location_id.id)
                substract_quantity = location_orderpoints._quantity_in_progress()

                for group in location_data['groups']:
                    if group.get('from_date'):
                        product_context['from_date'] = group['from_date'].strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if group['to_date']:
                        product_context['to_date'] = group['to_date'].strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    product_quantity = location_data['products'].with_context(product_context)._product_available()
                    for orderpoint in location_orderpoints:
                        try:
                            op_product_virtual = product_quantity[orderpoint.product_id.id]['virtual_available']
                            if op_product_virtual is None:
                                continue
                            if float_compare(op_product_virtual, orderpoint.product_min_qty, precision_rounding=orderpoint.product_uom.rounding) <= 0:
                                qty = max(orderpoint.product_min_qty, orderpoint.product_max_qty) - op_product_virtual
                                remainder = orderpoint.qty_multiple > 0 and qty % orderpoint.qty_multiple or 0.0

                                if float_compare(remainder, 0.0, precision_rounding=orderpoint.product_uom.rounding) > 0:
                                    qty += orderpoint.qty_multiple - remainder

                                if float_compare(qty, 0.0, precision_rounding=orderpoint.product_uom.rounding) < 0:
                                    continue

                                qty -= substract_quantity[orderpoint.id]
                                qty_rounded = float_round(qty, precision_rounding=orderpoint.product_uom.rounding)
                                if qty_rounded > 0:
                                    values = orderpoint._prepare_procurement_values(qty_rounded, **group['procurement_values'])
                                    try:
                                        with self._cr.savepoint():
                                            #TODO: make it batch
                                            self.env['procurement.group'].run([self.env['procurement.group'].Procurement(
                                                orderpoint.product_id, qty_rounded, orderpoint.product_uom,
                                                orderpoint.location_id, orderpoint.name, orderpoint.name,
                                                orderpoint.company_id, values)])
                                    except UserError as error:
                                        self.env['stock.rule']._log_next_activity(orderpoint.product_id, error.name)
                                    self._procurement_from_orderpoint_post_process([orderpoint.id])
                                if use_new_cursor:
                                    cr.commit()

                        except OperationalError:
                            if use_new_cursor:
                                orderpoints_noprefetch += [orderpoint.id]
                                cr.rollback()
                                continue
                            else:
                                raise

            try:
                if use_new_cursor:
                    cr.commit()
            except OperationalError:
                if use_new_cursor:
                    cr.rollback()
                    continue
                else:
                    raise

            if use_new_cursor:
                cr.commit()
                cr.close()

        return {}
