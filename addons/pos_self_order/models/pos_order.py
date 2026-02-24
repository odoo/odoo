# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, models, fields, api
from odoo.tools import float_round


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    combo_id = fields.Many2one('product.combo', string='Combo reference')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if (vals.get('combo_parent_uuid')):
                vals.update([
                    ('combo_parent_id', self.search([('uuid', '=', vals.get('combo_parent_uuid'))]).id)
                ])
            if 'combo_parent_uuid' in vals:
                del vals['combo_parent_uuid']
        return super().create(vals_list)

    def write(self, vals):
        if (vals.get('combo_parent_uuid')):
            vals.update([
                ('combo_parent_id', self.search([('uuid', '=', vals.get('combo_parent_uuid'))]).id)
            ])
        if 'combo_parent_uuid' in vals:
            del vals['combo_parent_uuid']
        return super().write(vals)

class PosOrder(models.Model):
    _inherit = "pos.order"

    table_stand_number = fields.Char(string="Table Stand Number")

    @api.model
    def _load_pos_self_data_domain(self, data):
        return [('id', '=', False)]

    @api.model
    def sync_from_ui(self, orders):
        for order in orders:
            if order.get('id'):
                order_id = order['id']

                if isinstance(order_id, int):
                    old_order = self.env['pos.order'].browse(order_id)
                    if old_order.takeaway:
                        order['takeaway'] = old_order.takeaway

        result = super().sync_from_ui(orders)
        order_ids = self.browse([order['id'] for order in result['pos.order'] if order.get('id')])
        self._send_notification(order_ids)
        return result

    @api.model
    def remove_from_ui(self, server_ids):
        order_ids = self.env['pos.order'].browse(server_ids)
        order_ids.state = 'cancel'
        self._send_notification(order_ids)
        return super().remove_from_ui(server_ids)

    def _send_notification(self, order_ids):
        config_ids = order_ids.config_id
        for config in config_ids:
            config.notify_synchronisation(config.current_session_id.id, self.env.context.get('login_number', 0))
            config._notify('ORDER_STATE_CHANGED', {})

    @api.model
    def _check_pos_order_lines(self, pos_config, order, line, fiscal_position_id):
        existing_order = pos_config.env['pos.order'].browse(order.get('id'))
        existing_lines = existing_order.lines if existing_order.exists() else pos_config.env['pos.order.line']

        if line[0] == Command.DELETE and line[1] in existing_lines.ids:
            return [Command.DELETE, line[1]]
        if line[0] == Command.UNLINK and line[1] in existing_lines.ids:
            return [Command.UNLINK, line[1]]
        if line[0] == Command.CREATE or line[0] == Command.UPDATE:
            line_data = line[2]

            product = pos_config.env['product.product'].browse(line_data.get('product_id'))
            tax_ids = fiscal_position_id.map_tax(product.taxes_id)

            return [Command.CREATE, 0, {
                'combo_id': line_data.get('combo_id'),
                'product_id': line_data.get('product_id'),
                'tax_ids': tax_ids.ids,
                'attribute_value_ids': [data for data in line_data.get('attribute_value_ids', []) if isinstance(data[1], int) and data[0] == 4],
                'price_unit': line_data.get('price_unit'),
                'qty': line_data.get('qty'),
                'price_subtotal': line_data.get('price_subtotal'),
                'price_subtotal_incl': line_data.get('price_subtotal_incl'),
                'price_extra': line_data.get('price_extra'),
                'price_type': line_data.get('price_type'),
                'full_product_name': line_data.get('full_product_name'),
                'customer_note': line_data.get('customer_note'),
                'uuid': line_data.get('uuid'),
                'id': line_data.get('id'),
                'order_id': existing_order.id if existing_order.exists() else None,
                'combo_parent_id': line_data.get('combo_parent_id'),
                'combo_item_id': line_data.get('combo_item_id'),
                'combo_line_ids': [id for id in line_data.get('combo_line_ids', []) if isinstance(id, int)],
            }]
        return []

    @api.model
    def _check_pos_order(self, pos_config, order, table):
        company = pos_config.company_id

        is_takeaway = order.get('takeaway')
        fiscal_position = pos_config.takeaway_fp_id if is_takeaway else pos_config.default_fiscal_position_id
        pricelist_id = pos_config.pricelist_id
        lines = [self._check_pos_order_lines(pos_config, order, line, fiscal_position) for line in order.get('lines', [])]
        partner_id = order.get('partner_id')
        partner = pos_config.env['res.partner'].browse(partner_id) if partner_id else None

        return {
            'id': order.get('id'),
            'table_stand_number': order.get('table_stand_number'),
            'access_token': order.get('access_token'),
            'customer_count': order.get('customer_count'),
            'table_id': table.id if table else None,
            'last_order_preparation_change': order.get('last_order_preparation_change'),
            'date_order': str(fields.Datetime.now()),
            'amount_difference': order.get('amount_difference'),
            'amount_tax': order.get('amount_tax'),
            'amount_total': order.get('amount_total'),
            'amount_paid': order.get('amount_paid'),
            'amount_return': order.get('amount_return'),
            'company_id': company.id,
            'pricelist_id': pricelist_id.id if pricelist_id else False,
            'partner_id': order.get('partner_id'),
            'sequence_number': order.get('sequence_number'),
            'session_id': pos_config.current_session_id.id,
            'takeaway': is_takeaway,
            'fiscal_position_id': fiscal_position.id if fiscal_position else False,
            'tracking_number': order.get('tracking_number'),
            'email': partner.email if partner else order.get('email'),
            'mobile': order.get('mobile'),
            'state': order.get('state'),
            'account_move': order.get('account_move'),
            'floating_order_name': order.get('floating_order_name'),
            'general_note': order.get('general_note'),
            'nb_print': order.get('nb_print'),
            'pos_reference': order.get('pos_reference'),
            'name': order.get('name'),
            'to_invoice': order.get('to_invoice'),
            'shipping_date': order.get('shipping_date'),
            'is_tipped': order.get('is_tipped'),
            'tip_amount': order.get('tip_amount'),
            'ticket_code': order.get('ticket_code'),
            'uuid': order.get('uuid'),
            'has_deleted_line': order.get('has_deleted_line'),
            'lines': lines,
        }

    def recompute_prices(self):
        self.ensure_one()
        company = self.company_id

        for line in self.lines:
            if len(line.combo_line_ids):
                self._compute_combo_price(line)
            elif not line.combo_parent_id:
                self._compute_line_price(line)

        order_lines = self.lines
        base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
        self.env['account.tax']._add_tax_details_in_base_lines(base_lines, company)
        self.env['account.tax']._round_base_lines_tax_details(base_lines, company)
        tax_totals = self.env['account.tax']._get_tax_totals_summary(
            base_lines=base_lines,
            currency=self.currency_id or company.currency_id,
            company=company,
        )
        self.amount_tax = tax_totals['tax_amount_currency']
        self.amount_total = tax_totals['total_amount_currency']

    def _compute_line_price(self, line):
        company = self.company_id
        pricelist = self.pricelist_id
        selected_attributes = line.attribute_value_ids
        product = line.product_id.with_context(line.product_id._get_product_price_context(selected_attributes))
        tax_domain = self.env['account.tax']._check_company_domain(company)

        price = pricelist._get_product_price(product, line.qty or 1.0, currency=self.currency_id)
        line.tax_ids = product.taxes_id.filtered_domain(tax_domain)
        tax_ids_after_fiscal_position = self.fiscal_position_id.map_tax(line.tax_ids)
        new_price = self.env['account.tax']._fix_tax_included_price_company(
            price, line.tax_ids, tax_ids_after_fiscal_position, self.company_id)

        line.price_unit = new_price
        base_line = line._prepare_base_line_for_taxes_computation()
        self.env['account.tax']._add_tax_details_in_base_line(base_line, company)
        self.env['account.tax']._round_base_lines_tax_details([base_line], company)
        line.price_subtotal = base_line['tax_details']['total_excluded_currency']
        line.price_subtotal_incl = base_line['tax_details']['total_included_currency']

    def _compute_combo_price(self, parent_line):
        """
        This method is a python version of odoo/addons/point_of_sale/static/src/app/models/utils/compute_combo_items.js
        It is used to compute the price of combo items on the server side when an order is received from
        the POS frontend. In an accounting perspective, isn't correct but we still waiting the combo
        computation from accounting side.
        """
        pos_config = self.config_id
        sale_price_digits = self.env['decimal.precision'].precision_get('Product Price')
        takeaway = self.takeaway

        pricelist = pos_config.pricelist_id
        product = parent_line.product_id
        lst_price = pricelist._get_product_price(product, quantity=parent_line.qty) if pricelist else product.lst_price
        selected_attributes = parent_line.attribute_value_ids
        lst_price += sum(selected_attributes.mapped('price_extra'))
        price_extra = sum(attr.price_extra for attr in selected_attributes)
        lst_price += price_extra

        fiscal_pos = pos_config.default_fiscal_position_id
        if takeaway and pos_config.takeaway_fp_id:
            fiscal_pos = pos_config.takeaway_fp_id

        original_total = sum(parent_line.combo_line_ids.mapped("combo_item_id").combo_id.mapped("base_price"))
        remaining_total = lst_price
        factor = lst_price / original_total if original_total > 0 else 1

        for i, pos_order_line in enumerate(parent_line.combo_line_ids):
            child_product = pos_order_line.product_id
            price_unit = float_round(pos_order_line.combo_item_id.combo_id.base_price * factor, precision_digits=sale_price_digits)
            remaining_total -= price_unit

            if i == len(parent_line.combo_line_ids) - 1:
                price_unit += remaining_total

            selected_attributes = pos_order_line.attribute_value_ids
            price_extra_child = sum(attr.price_extra for attr in selected_attributes)
            price_unit += pos_order_line.combo_item_id.extra_price + price_extra_child

            taxes = fiscal_pos.map_tax(child_product.taxes_id) if fiscal_pos else child_product.taxes_id
            pdetails = taxes.compute_all(price_unit, pos_config.currency_id, pos_order_line.qty, child_product)

            pos_order_line.write({
                'price_unit': price_unit,
                'price_subtotal': pdetails.get('total_excluded'),
                'price_subtotal_incl': pdetails.get('total_included'),
                'price_extra': price_extra_child,
                'tax_ids': child_product.taxes_id,
            })
        lst_price = 0
