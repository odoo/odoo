# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        #inherit of the function from account.move to validate a new tax and the priceunit of a downpayment
        res = super(AccountMove, self).action_post()
        line_ids = self.mapped('line_ids').filtered(lambda line: line.sale_line_ids.is_downpayment)
        for line in line_ids:
            try:
                line.sale_line_ids.tax_id = line.tax_ids
                if all(line.tax_ids.mapped('price_include')):
                    line.sale_line_ids.price_unit = line.price_unit
                else:
                    #To keep positive amount on the sale order and to have the right price for the invoice
                    #We need the - before our untaxed_amount_to_invoice
                    line.sale_line_ids.price_unit = -line.sale_line_ids.untaxed_amount_to_invoice
            except UserError:
                # a UserError here means the SO was locked, which prevents changing the taxes
                # just ignore the error - this is a nice to have feature and should not be blocking
                pass
        return res

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    sale_line_ids = fields.Many2many(
        'sale.order.line',
        'sale_order_line_invoice_rel',
        'invoice_line_id', 'order_line_id',
        string='Sales Order Lines', readonly=True, copy=False)

    def _copy_data_extend_business_fields(self, values):
        # OVERRIDE to copy the 'sale_line_ids' field as well.
        super(AccountMoveLine, self)._copy_data_extend_business_fields(values)
        values['sale_line_ids'] = [(6, None, self.sale_line_ids.ids)]

    def _prepare_analytic_line(self):
        """ Note: This method is called only on the move.line that having an analytic account, and
            so that should create analytic entries.
        """
        values_list = super(AccountMoveLine, self)._prepare_analytic_line()

        # filter the move lines that can be reinvoiced: a cost (negative amount) analytic line without SO line but with a product can be reinvoiced
        move_to_reinvoice = self.env['account.move.line']
        for index, move_line in enumerate(self):
            values = values_list[index]
            if 'so_line' not in values:
                if move_line._sale_can_be_reinvoice():
                    move_to_reinvoice |= move_line

        # insert the sale line in the create values of the analytic entries
        if move_to_reinvoice:
            map_sale_line_per_move = move_to_reinvoice._sale_create_reinvoice_sale_line()

            for values in values_list:
                sale_line = map_sale_line_per_move.get(values.get('move_id'))
                if sale_line:
                    values['so_line'] = sale_line.id

        return values_list

    def _sale_can_be_reinvoice(self):
        """ determine if the generated analytic line should be reinvoiced or not.
            For Vendor Bill flow, if the product has a 'erinvoice policy' and is a cost, then we will find the SO on which reinvoice the AAL
        """
        self.ensure_one()
        if self.sale_line_ids:
            return False
        uom_precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        return float_compare(self.credit or 0.0, self.debit or 0.0, precision_digits=uom_precision_digits) != 1 and self.product_id.expense_policy not in [False, 'no']

    def _sale_create_reinvoice_sale_line(self):

        sale_order_map = self._sale_determine_order()

        sale_line_values_to_create = []  # the list of creation values of sale line to create.
        existing_sale_line_cache = {}  # in the sales_price-delivery case, we can reuse the same sale line. This cache will avoid doing a search each time the case happen
        # `map_move_sale_line` is map where
        #   - key is the move line identifier
        #   - value is either a sale.order.line record (existing case), or an integer representing the index of the sale line to create in
        #     the `sale_line_values_to_create` (not existing case, which will happen more often than the first one).
        map_move_sale_line = {}

        for move_line in self:
            sale_order = sale_order_map.get(move_line.id)

            # no reinvoice as no sales order was found
            if not sale_order:
                continue

            # raise if the sale order is not currenlty open
            if sale_order.state != 'sale':
                message_unconfirmed = _('The Sales Order %s linked to the Analytic Account %s must be validated before registering expenses.')
                messages = {
                    'draft': message_unconfirmed,
                    'sent': message_unconfirmed,
                    'done': _('The Sales Order %s linked to the Analytic Account %s is currently locked. You cannot register an expense on a locked Sales Order. Please create a new SO linked to this Analytic Account.'),
                    'cancel': _('The Sales Order %s linked to the Analytic Account %s is cancelled. You cannot register an expense on a cancelled Sales Order.'),
                }
                raise UserError(messages[sale_order.state] % (sale_order.name, sale_order.analytic_account_id.name))

            price = move_line._sale_get_invoice_price(sale_order)

            # find the existing sale.line or keep its creation values to process this in batch
            sale_line = None
            if move_line.product_id.expense_policy == 'sales_price' and move_line.product_id.invoice_policy == 'delivery':  # for those case only, we can try to reuse one
                map_entry_key = (sale_order.id, move_line.product_id.id, price)  # cache entry to limit the call to search
                sale_line = existing_sale_line_cache.get(map_entry_key)
                if sale_line:  # already search, so reuse it. sale_line can be sale.order.line record or index of a "to create values" in `sale_line_values_to_create`
                    map_move_sale_line[move_line.id] = sale_line
                    existing_sale_line_cache[map_entry_key] = sale_line
                else:  # search for existing sale line
                    sale_line = self.env['sale.order.line'].search([
                        ('order_id', '=', sale_order.id),
                        ('price_unit', '=', price),
                        ('product_id', '=', move_line.product_id.id),
                        ('is_expense', '=', True),
                    ], limit=1)
                    if sale_line:  # found existing one, so keep the browse record
                        map_move_sale_line[move_line.id] = existing_sale_line_cache[map_entry_key] = sale_line
                    else:  # should be create, so use the index of creation values instead of browse record
                        # save value to create it
                        sale_line_values_to_create.append(move_line._sale_prepare_sale_line_values(sale_order, price))
                        # store it in the cache of existing ones
                        existing_sale_line_cache[map_entry_key] = len(sale_line_values_to_create) - 1  # save the index of the value to create sale line
                        # store it in the map_move_sale_line map
                        map_move_sale_line[move_line.id] = len(sale_line_values_to_create) - 1  # save the index of the value to create sale line

            else:  # save its value to create it anyway
                sale_line_values_to_create.append(move_line._sale_prepare_sale_line_values(sale_order, price))
                map_move_sale_line[move_line.id] = len(sale_line_values_to_create) - 1  # save the index of the value to create sale line

        # create the sale lines in batch
        new_sale_lines = self.env['sale.order.line'].create(sale_line_values_to_create)
        for sol in new_sale_lines:
            if sol.product_id.expense_policy != 'cost':
                sol._onchange_discount()

        # build result map by replacing index with newly created record of sale.order.line
        result = {}
        for move_line_id, unknown_sale_line in map_move_sale_line.items():
            if isinstance(unknown_sale_line, int):  # index of newly created sale line
                result[move_line_id] = new_sale_lines[unknown_sale_line]
            elif isinstance(unknown_sale_line, models.BaseModel):  # already record of sale.order.line
                result[move_line_id] = unknown_sale_line
        return result

    def _sale_determine_order(self):
        """ Get the mapping of move.line with the sale.order record on which its analytic entries should be reinvoiced
            :return a dict where key is the move line id, and value is sale.order record (or None).
        """
        analytic_accounts = self.mapped('analytic_account_id')

        # link the analytic account with its open SO by creating a map: {AA.id: sale.order}, if we find some analytic accounts
        mapping = {}
        if analytic_accounts:  # first, search for the open sales order
            sale_orders = self.env['sale.order'].search([('analytic_account_id', 'in', analytic_accounts.ids), ('state', '=', 'sale')], order='create_date DESC')
            for sale_order in sale_orders:
                mapping[sale_order.analytic_account_id.id] = sale_order

            analytic_accounts_without_open_order = analytic_accounts.filtered(lambda account: not mapping.get(account.id))
            if analytic_accounts_without_open_order:  # then, fill the blank with not open sales orders
                sale_orders = self.env['sale.order'].search([('analytic_account_id', 'in', analytic_accounts_without_open_order.ids)], order='create_date DESC')
            for sale_order in sale_orders:
                mapping[sale_order.analytic_account_id.id] = sale_order

        # map of AAL index with the SO on which it needs to be reinvoiced. Maybe be None if no SO found
        return {move_line.id: mapping.get(move_line.analytic_account_id.id) for move_line in self}

    def _sale_prepare_sale_line_values(self, order, price):
        """ Generate the sale.line creation value from the current move line """
        self.ensure_one()
        last_so_line = self.env['sale.order.line'].search([('order_id', '=', order.id)], order='sequence desc', limit=1)
        last_sequence = last_so_line.sequence + 1 if last_so_line else 100

        fpos = order.fiscal_position_id or order.fiscal_position_id.get_fiscal_position(order.partner_id.id)
        taxes = fpos.map_tax(self.product_id.taxes_id, self.product_id, order.partner_id)

        return {
            'order_id': order.id,
            'name': self.name,
            'sequence': last_sequence,
            'price_unit': price,
            'tax_id': [x.id for x in taxes],
            'discount': 0.0,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': 0.0,
            'is_expense': True,
        }

    def _sale_get_invoice_price(self, order):
        """ Based on the current move line, compute the price to reinvoice the analytic line that is going to be created (so the
            price of the sale line).
        """
        self.ensure_one()

        unit_amount = self.quantity
        amount = (self.credit or 0.0) - (self.debit or 0.0)

        if self.product_id.expense_policy == 'sales_price':
            product = self.product_id.with_context(
                partner=order.partner_id.id,
                date_order=order.date_order,
                pricelist=order.pricelist_id.id,
                uom=self.product_uom_id.id,
                quantity=unit_amount
            )
            if order.pricelist_id.discount_policy == 'with_discount':
                return product.price
            return product.lst_price

        uom_precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        if float_is_zero(unit_amount, precision_digits=uom_precision_digits):
            return 0.0

        # Prevent unnecessary currency conversion that could be impacted by exchange rate
        # fluctuations
        if self.company_id.currency_id and amount and self.company_id.currency_id == order.currency_id:
            return abs(amount / unit_amount)

        price_unit = abs(amount / unit_amount)
        currency_id = self.company_id.currency_id
        if currency_id and currency_id != order.currency_id:
            price_unit = currency_id._convert(price_unit, order.currency_id, order.company_id, order.date_order or fields.Date.today())
        return price_unit
