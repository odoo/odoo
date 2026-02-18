# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import Command, models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


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
    self_ordering_table_id = fields.Many2one('restaurant.table', string='Table reference', readonly=True)
    source = fields.Selection(selection_add=[
        ('mobile', 'Self-Order Mobile'),
        ('kiosk', 'Self-Order Kiosk')
    ])

    def write(self, vals):
        if 'table_id' in vals and self.self_ordering_table_id:
            # Clear stale self-order table link when the order is transferred to a new table.
            vals['self_ordering_table_id'] = vals['table_id']
        return super().write(vals)

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        return [('id', '=', False)]

    @api.model
    def remove_from_ui(self, server_ids):
        order_ids = self.env['pos.order'].browse(server_ids)
        order_ids.state = 'cancel'
        self._send_notification(order_ids)
        return super().remove_from_ui(server_ids)

    @api.model
    def sync_from_ui(self, orders):
        result = super().sync_from_ui(orders)
        order_ids = self.browse([order['id'] for order in result['pos.order'] if order.get('id')])
        self._send_notification(order_ids)
        return result

    def action_pos_order_cancel(self):
        orders = super().action_pos_order_cancel()
        success_orders_ids = [o['id'] for o in orders['pos.order'] if o['state'] == 'cancel']
        orders_ids = self.browse(success_orders_ids)
        self._send_notification(orders_ids)
        return orders

    def _send_notification(self, order_ids):
        config_ids = order_ids.config_id
        for config in config_ids:
            config.notify_synchronisation(config.current_session_id.id, self.env.context.get('device_identifier', 0))
            config._notify('ORDER_STATE_CHANGED', {})

    def _send_self_order_receipt(self):
        if self.email:
            try:
                self.action_send_self_order_receipt(self.email, self.preset_id.mail_template_id.id, False, False)
            except UserError as e:
                _logger.warning("Error while sending email: %s", e.args[0])

    def action_send_self_order_receipt(self, email, mail_template_id, ticket_image, basic_image):
        self.ensure_one()
        self.email = email
        mail_template = self.env['mail.template'].browse(mail_template_id)
        if not mail_template:
            raise UserError(_("The mail template with xmlid %s has been deleted.", mail_template_id))
        email_values = {'email_to': email}
        if self.state == 'paid' and ticket_image:
            email_values['attachment_ids'] = self._get_mail_attachments(self.name, ticket_image, basic_image)
        mail_template.send_mail(self.id, force_send=True, email_values=email_values)

    def _send_payment_result(self, payment_result):
        self.ensure_one()
        self.config_id._notify('PAYMENT_STATUS', {
            'payment_result': payment_result,
            'data': {
                'pos.order': self.read(self._load_pos_self_data_fields(self.config_id), load=False),
                'pos.order.line': self.lines.read(self.lines._load_pos_self_data_fields(self.config_id), load=False),
            }
        })
        if payment_result == 'Success':
            self._send_order()

    def _load_pos_self_data_fields(self, config):
        return ['id', 'uuid', 'name', 'display_name', 'access_token', 'last_order_preparation_change', 'date_order', 'amount_total', 'amount_paid', 'amount_return', 'user_id', 'amount_tax', 'lines', 'pricelist_id', 'company_id', 'country_code', 'sequence_number', 'session_id',
                'config_id', 'currency_id', 'currency_rate', 'is_refund', 'has_refundable_lines', 'state', 'account_move', 'preset_id', 'floating_order_name', 'general_customer_note', 'internal_note', 'nb_print', 'pos_reference', 'fiscal_position_id', 'payment_ids', 'to_invoice',
                'shipping_date', 'preset_time', 'is_invoiced', 'is_tipped', 'tip_amount', 'ticket_code', 'tracking_number', 'email', 'mobile', 'table_id', 'course_ids',
                'table_stand_number', 'self_ordering_table_id', 'create_date', 'write_date', 'source', 'partner_id', 'customer_count']

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
                'attribute_value_ids': [id for id in line_data.get('attribute_value_ids', []) if isinstance(id, int)],
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
    def _check_pos_order(self, pos_config, order, device_type, table=None):
        company = pos_config.company_id
        preset_id = order['preset_id'] if pos_config.use_presets else False
        preset_id = pos_config.env['pos.preset'].browse(preset_id) if preset_id else False
        floating_order_name = order.get('floating_order_name')

        if not preset_id and pos_config.use_presets:
            raise UserError(_("Invalid preset"))

        pos_reference, tracking_number = pos_config._get_next_order_refs()
        prefix = f"K{pos_config.id}-" if device_type == "kiosk" else "S"
        fiscal_position_id = preset_id.fiscal_position_id if preset_id else pos_config.default_fiscal_position_id
        pricelist_id = preset_id.pricelist_id if preset_id else pos_config.pricelist_id
        lines = [self._check_pos_order_lines(pos_config, order, line, fiscal_position_id) for line in order.get('lines', [])]
        partner_id = order.get('partner_id')
        partner = pos_config.env['res.partner'].browse(partner_id) if partner_id else None

        if device_type == 'kiosk':
            floating_order_name = f"Table tracker {order['table_stand_number']}" if order.get('table_stand_number') else tracking_number

        if not order.get('floating_order_name') and table:
            floating_order_name = f"Self-Order T {table.table_number}"
        elif not order.get('floating_order_name'):
            floating_order_name = f"Self-Order {tracking_number}"

        return {
            'id': order.get('id'),
            'table_stand_number': order.get('table_stand_number'),
            'access_token': order.get('access_token'),
            'customer_count': order.get('customer_count'),
            'self_ordering_table_id': table.id if table else False,
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
            'fiscal_position_id': fiscal_position_id.id if fiscal_position_id else False,
            'preset_id': preset_id.id if preset_id else False,
            'preset_time': order.get('preset_time'),
            'tracking_number': f"{prefix}{tracking_number}",
            'source': 'kiosk' if device_type == 'kiosk' else 'mobile',
            'email': partner.email if partner else order.get('email'),
            'mobile': order.get('mobile'),
            'state': order.get('state'),
            'account_move': order.get('account_move'),
            'floating_order_name': floating_order_name,
            'general_customer_note': order.get('general_customer_note'),
            'nb_print': order.get('nb_print'),
            'pos_reference': pos_reference,
            'to_invoice': order.get('to_invoice'),
            'shipping_date': order.get('shipping_date'),
            'is_tipped': order.get('is_tipped'),
            'tip_amount': order.get('tip_amount'),
            'ticket_code': order.get('ticket_code'),
            'uuid': order.get('uuid'),
            'has_deleted_line': order.get('has_deleted_line'),
            'lines': lines,
            'relations_uuid_mapping': order.get('relations_uuid_mapping', {}),
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
        child_lines = parent_line.combo_line_ids
        currency = parent_line.order_id.currency_id
        taxes = self.fiscal_position_id.map_tax(parent_line.product_id.taxes_id)
        parent_line.tax_ids = taxes
        parent_lst_price = self.pricelist_id._get_product_price(parent_line.product_id, parent_line.qty)
        child_line_free = []
        child_line_extra = []

        child_lines_by_combo = {}
        for line in child_lines:
            combo = line.combo_item_id.combo_id
            child_lines_by_combo.setdefault(combo, []).append(line)

        for combo, child_lines in child_lines_by_combo.items():
            free_count = 0
            max_free = combo.qty_free

            for line in child_lines:
                qty_free = max(0, max_free - free_count)
                free_qty = min(line.qty, qty_free)
                extra_qty = line.qty - free_qty

                if free_qty > 0:
                    child_line_free.append(line)
                    free_count += free_qty

                if extra_qty > 0:
                    child_line_extra.append(line)

        original_total = sum(line.combo_item_id.combo_id.base_price * line.qty for line in child_line_free if line.combo_item_id.combo_id.qty_free > 0)
        remaining_total = parent_lst_price

        for index, child in enumerate(child_line_free):
            combo_item = child.combo_item_id
            combo = combo_item.combo_id
            unit_devision_factor = original_total or 1
            price_unit = currency.round(combo.base_price * parent_lst_price / unit_devision_factor)
            remaining_total -= price_unit * child.qty

            if index == len(child_line_free) - 1:
                price_unit += remaining_total

            selected_attributes = child.attribute_value_ids
            price_extra = sum(attr.price_extra for attr in selected_attributes)
            total_price = price_unit + price_extra + child.combo_item_id.extra_price
            child.price_unit = total_price

        for child in child_line_extra:
            combo_item = child.combo_item_id
            price_unit = currency.round(combo_item.combo_id.base_price)
            selected_attributes = child.attribute_value_ids
            price_extra = sum(attr.price_extra for attr in selected_attributes)
            total_price = price_unit + price_extra + child.combo_item_id.extra_price
            child.price_unit = total_price
