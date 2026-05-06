from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.tools import float_compare, float_is_zero, split_every
from odoo.tools.constants import PREFETCH_MAX


class PosSession(models.Model):
    _inherit = 'pos.session'

    failed_pickings = fields.Boolean(compute='_compute_picking_count')
    picking_count = fields.Integer(compute='_compute_picking_count')
    picking_ids = fields.One2many('stock.picking', 'pos_session_id')
    update_stock_at_closing = fields.Boolean('Stock should be updated at closing')

    @api.depends('picking_ids', 'picking_ids.state')
    def _compute_picking_count(self):
        for session in self:
            session.picking_count = self.env['stock.picking'].search_count([('pos_session_id', 'in', session.ids)])
            session.failed_pickings = bool(self.env['stock.picking'].search_count([('pos_session_id', 'in', session.ids), ('state', '!=', 'done')], limit=1))

    @api.depends('sales_move_id', 'refunds_move_id')
    def _compute_move_ids(self):
        super()._compute_move_ids()
        for session in self:
            session.move_ids |= session.picking_ids.move_ids.account_move_id

    def action_stock_picking(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_ready')
        action['display_name'] = self.env._('Pickings')
        action['context'] = {}
        action['domain'] = [('id', 'in', self.picking_ids.ids)]
        return action

    @api.model
    def _load_pos_data_models(self, config):
        pos_data_models = super()._load_pos_data_models(config)
        pos_data_models.extend(['stock.picking.type', 'pos.pack.operation.lot'])
        return pos_data_models

    @api.model
    def _load_pos_data_fields(self, config):
        pos_data_fields = super()._load_pos_data_fields(config)
        pos_data_fields.append('update_stock_at_closing')
        return pos_data_fields

    def close_session_from_ui(self, payment_method_closing={}):
        result = super().close_session_from_ui(payment_method_closing)
        if self.update_stock_at_closing:
            self._create_picking_at_end_of_session()
            self._get_closed_orders().filtered(lambda o: not o.is_total_cost_computed)._compute_total_cost_at_session_closing()
        self.picking_ids.move_ids.sudo()._trigger_scheduler()
        return result

    def _create_picking_at_end_of_session(self):
        self.ensure_one()
        lines_grouped_by_dest_location = {}
        picking_type = self.config_id.picking_type_id

        if not picking_type or not picking_type.default_location_dest_id:
            session_destination_id = self.env['stock.warehouse']._get_partner_locations()[0].id
        else:
            session_destination_id = picking_type.default_location_dest_id.id

        for order in self._get_closed_orders():
            if order._force_create_picking_real_time() or order.shipping_date:
                continue
            destination_id = order.partner_id.property_stock_customer.id or session_destination_id
            if destination_id in lines_grouped_by_dest_location:
                lines_grouped_by_dest_location[destination_id] |= order.lines
            else:
                lines_grouped_by_dest_location[destination_id] = order.lines

        for location_dest_id, lines in lines_grouped_by_dest_location.items():
            pickings = self.env['stock.picking']._create_picking_from_pos_order_lines(location_dest_id, lines, picking_type)
            pickings.write({'pos_session_id': self.id, 'origin': self.name})

    def _get_account_move_data(self, bank_payment_method_diffs):
        data = super()._get_account_move_data(bank_payment_method_diffs)
        return self._create_stock_valuation_lines(data)

    def _get_rounding_difference_vals(self, amount, amount_converted):
        if self.config_id.cash_rounding:
            partial_args = {
                'name': 'Rounding line',
                'move_id': self.move_id.id,
            }
            if float_compare(0.0, amount, precision_rounding=self.currency_id.rounding) > 0:    # loss
                partial_args['account_id'] = self.config_id.rounding_method.loss_account_id.id
                return self._debit_amounts(partial_args, -amount, -amount_converted)

            if float_compare(0.0, amount, precision_rounding=self.currency_id.rounding) < 0:   # profit
                partial_args['account_id'] = self.config_id.rounding_method.profit_account_id.id
                return self._credit_amounts(partial_args, amount, amount_converted)
        return None

    def _create_non_reconciliable_move_lines(self, data):
        data = super()._create_non_reconciliable_move_lines(data)
        stock_expense = data.get('stock_expense')
        rounding_difference = data.get('rounding_difference')
        MoveLine = data.get('MoveLine')
        rounding_vals = []

        if not float_is_zero(rounding_difference['amount'], precision_rounding=self.currency_id.rounding) or not float_is_zero(rounding_difference['amount_converted'], precision_rounding=self.currency_id.rounding):
            rounding_vals = [self._get_rounding_difference_vals(rounding_difference['amount'], rounding_difference['amount_converted'])]

        MoveLine.create(
            [self._get_stock_expense_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in stock_expense.items()]
            + rounding_vals,
        )

        return data

    def _create_stock_valuation_lines(self, data):
        MoveLine = data.get('MoveLine')
        stock_valuation = data.get('stock_valuation')
        stock_return = data.get('stock_return')

        stock_valuation_vals = defaultdict(list)
        stock_valuation_lines = {}
        for stock_moves in [stock_valuation, stock_return]:
            for account, amounts in stock_moves.items():
                stock_valuation_vals[account].append(self._get_stock_valuation_vals(account, amounts['amount'], amounts['amount_converted']))

        for stock_valuation_acc, vals in stock_valuation_vals.items():
            stock_valuation_lines[stock_valuation_acc] = MoveLine.create(vals)

        data.update({'stock_valuation_lines': stock_valuation_lines})
        return data

    def _get_stock_expense_vals(self, exp_account, amount, amount_converted):
        partial_args = {'account_id': exp_account.id, 'move_id': self.move_id.id}
        return self._debit_amounts(partial_args, amount, amount_converted, force_company_currency=True)

    def _get_stock_valuation_vals(self, stock_val_account, amount, amount_converted):
        partial_args = {'account_id': stock_val_account.id, 'move_id': self.move_id.id}
        return self._credit_amounts(partial_args, amount, amount_converted, force_company_currency=True)

    def _get_related_account_moves(self):
        related_account_moves = super()._get_related_account_moves()
        pickings = self.picking_ids | self._get_closed_orders().mapped('picking_ids')
        stock_account_moves = pickings.move_ids.account_move_id
        return related_account_moves | stock_account_moves

    @api.model
    def _get_default_session_vals(self, config_id):
        config_vals = super()._get_default_session_vals(config_id)
        pos_config = self.env['pos.config'].browse(config_id)
        config_vals['update_stock_at_closing'] = pos_config.company_id.point_of_sale_update_stock_quantities == "closing"
        return config_vals

    def _prepare_session_closing_extra_line_commands(self, orders, refund, payments=[]):
        lines = super()._prepare_session_closing_extra_line_commands(orders, refund, payments)
        not_linked_to_order = self.picking_ids.filtered(lambda p: not p.pos_order_id).ids
        linked_to_order = orders.filtered(lambda order: not order.shipping_date).picking_ids.ids
        all_picking_ids = not_linked_to_order + linked_to_order

        if not all_picking_ids:
            return lines

        stock_move_sudo = self.env['stock.move'].sudo()
        stock_moves = stock_move_sudo.search([
            ('picking_id', 'in', all_picking_ids),
            ('product_id.valuation', '=', 'real_time'),
            ('product_id.is_storable', '=', True),
        ])

        for stock_moves_batch in split_every(PREFETCH_MAX, stock_moves._ids, stock_moves.browse):
            for move in stock_moves_batch:
                product_accounts = move.with_company(move.company_id).product_id._get_product_accounts()
                exp_key = product_accounts['expense']
                stock_key = product_accounts['stock_valuation']
                signed_product_qty = move.uom_id._compute_quantity(
                    move.product_uom_qty,
                    move.product_id.uom_id,
                    round=False,
                )

                if move._is_in():
                    signed_product_qty *= -1

                amount = signed_product_qty * move._get_price_unit()
                lines.append(Command.create({
                    'name': move.product_id.display_name,
                    'account_id': exp_key.id,
                    'partner_id': self.config_id.default_partner_id.id,
                    'quantity': signed_product_qty,
                    'amount_currency': amount,
                    'balance': amount,
                }))
                lines.append(Command.create({
                    'name': move.product_id.display_name,
                    'account_id': stock_key.id,
                    'partner_id': self.config_id.default_partner_id.id,
                    'quantity': -signed_product_qty,
                    'amount_currency': -amount,
                    'balance': -amount,
                }))

        return lines

    def _create_partial_reversal_move_from_session_closing(self, order):
        move = super()._create_partial_reversal_move_from_session_closing(order)
        if order.picking_ids.ids:
            reverse_move_lines = []
            commercial_partner = order.partner_id.commercial_partner_id
            stock_moves = self.env['stock.move'].sudo().search([
                ('picking_id', 'in', order.picking_ids.ids),
                ('product_id.valuation', '=', 'real_time'),
            ])

            for stock_move in stock_moves:
                product_ctx = stock_move.with_company(stock_move.company_id).product_id
                product_accounts = product_ctx._get_product_accounts()
                expense_account = product_accounts['expense']
                stock_account = product_accounts['stock_valuation']
                balance = stock_move.value if stock_move.is_out else -stock_move.value

                reverse_move_lines.append(Command.create({
                    'name': _("Stock variation for %s", stock_move.product_id.name),
                    'account_id': expense_account.id,
                    'partner_id': commercial_partner.id,
                    'currency_id': order.company_id.currency_id.id,
                    'amount_currency': -balance,
                    'balance': -balance,
                }))
                reverse_move_lines.append(Command.create({
                    'name': _("Stock variation for %s", stock_move.product_id.name),
                    'account_id': stock_account.id,
                    'partner_id': commercial_partner.id,
                    'currency_id': order.company_id.currency_id.id,
                    'amount_currency': balance,
                    'balance': balance,
                }))

            move.write({
                'line_ids': reverse_move_lines,
            })

        return move
