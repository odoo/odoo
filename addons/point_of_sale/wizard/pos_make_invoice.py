import pytz
from odoo.tools import float_compare, float_repr
from odoo import api, models, fields, _
from odoo.exceptions import UserError


class PosMakeInvoice(models.TransientModel):
    _description = 'Multiple order invoice creation'
    count = fields.Integer(string="Order Count", compute='_compute_count')
    pos_order_ids = fields.Many2many(
        'pos.order', default=lambda self: self.env.context.get('active_ids'))
    consolidated_billing = fields.Boolean(
        string="Consolidated Billing", default=True,
        help="Create one invoice for all orders related to same customer and same invoicing address"
    )

    @api.depends('pos_order_ids')
    def _compute_count(self):
        for wizard in self:
            wizard.count = len(wizard.pos_order_ids)

    def _prepare_invoice_lines(self):
        """ Prepare a list of ORM commands containing dictionaries to fill
        'invoice_line_ids' for a consolidated invoice across multiple orders.

        :return: A list of Command.create to fill 'invoice_line_ids' for account.move.
        """
        invoice_lines = []

        for order in self.pos_order_ids:
            line_values_list = order._prepare_tax_base_line_values()

            for line_values in line_values_list:
                line = line_values['record']
                invoice_lines_values = order._get_invoice_lines_values(line_values, line)
                invoice_lines.append((0, None, invoice_lines_values))

                is_percentage = order.pricelist_id and any(
                    order.pricelist_id.item_ids.filtered(lambda rule: rule.compute_price == "percentage")
                )

                if is_percentage and float_compare(line.price_unit, line.product_id.lst_price, precision_rounding=order.currency_id.rounding) < 0:
                    invoice_lines.append((0, None, {
                        'name': _('Price discount from %(original_price)s to %(discounted_price)s',
                                original_price=float_repr(line.product_id.lst_price, order.currency_id.decimal_places),
                                discounted_price=float_repr(line.price_unit, order.currency_id.decimal_places)),
                        'display_type': 'line_note',
                    }))

                if line.customer_note:
                    invoice_lines.append((0, None, {
                        'name': line.customer_note,
                        'display_type': 'line_note',
                    }))

        return invoice_lines

    def _prepare_invoice_vals(self, partner):
        timezone = pytz.timezone(self.env.user.tz or 'UTC')
        invoice_date = fields.Datetime.now()
        amount_total = sum(order.amount_total for order in self.pos_order_ids)

        pos_refunded_invoice_ids = []
        for order in self.pos_order_ids.mapped('lines'):
            if order.refunded_orderline_id and order.refunded_orderline_id.order_id.account_move:
                pos_refunded_invoice_ids.append(order.refunded_orderline_id.order_id.account_move.id)

        vals = {
            'invoice_origin': 'Combined',
            'pos_refunded_invoice_ids': pos_refunded_invoice_ids,
            'journal_id': self.pos_order_ids[0].session_id.config_id.invoice_journal_id.id,
            'move_type': 'out_invoice' if amount_total >= 0 else 'out_refund',
            'ref': ', '.join(self.pos_order_ids.mapped('name')),
            'partner_id': partner.address_get(['invoice'])['invoice'],
            'partner_bank_id': partner.bank_ids[0].id if partner.bank_ids else False,
            'currency_id': self.pos_order_ids[0].currency_id.id,
            'invoice_user_id': self.env.user.id,
            'invoice_date': invoice_date.astimezone(timezone).date(),
            'fiscal_position_id': self.pos_order_ids[0].fiscal_position_id.id,
            'invoice_line_ids': self._prepare_invoice_lines(),
            'invoice_payment_term_id': partner.property_payment_term_id.id or False,
            'invoice_cash_rounding_id': self.pos_order_ids[0].config_id.rounding_method.id
            if self.pos_order_ids[0].config_id.cash_rounding and
            (not self.pos_order_ids[0].config_id.only_round_cash_method or
                any(p.payment_method_id.is_cash_count for p in self.pos_order_ids[0].payment_ids))
            else False
        }

        if any(order.refunded_order_id.account_move for order in self.pos_order_ids):
            refunded_order = self.pos_order_ids.filtered(lambda o: o.refunded_order_id.account_move)
            vals['ref'] = _('Reversal of: %s', refunded_order[0].refunded_order_id.account_move.name)
            vals['reversed_entry_id'] = refunded_order[0].refunded_order_id.account_move.id

        if any(order.floating_order_name for order in self.pos_order_ids):
            vals.update({'narration': ', '.join(self.pos_order_ids.mapped('floating_order_name'))})

        return vals

    def create_invoices(self):
        self.ensure_one()

        if any(order_id for order_id in self.pos_order_ids if not order_id.partner_id):
            raise UserError("Some orders don't have a customer assigned.")
        invoices = self.env['account.move']
        if not self.consolidated_billing:
            for order in self.pos_order_ids:
                invoices |= order.action_pos_order_invoice(multi_invoice=True)
        else:
            for partner in self.pos_order_ids.partner_id:
                orders_by_partner = self.pos_order_ids.filtered(lambda o: o.partner_id == partner)

                if not orders_by_partner:
                    continue

                for config in orders_by_partner.mapped('config_id'):
                    orders = orders_by_partner.filtered(lambda o: o.config_id == config)

                    if not orders:
                        continue

                    move_vals = self._prepare_invoice_vals(partner)

                    line_vals = []
                    for order in orders:
                        for line in order.lines:
                            line_vals.append((0, 0, {
                                'product_id': line.product_id.id,
                                'quantity': line.qty,
                                'price_unit': line.price_unit,
                                'tax_ids': [(6, 0, line.tax_ids_after_fiscal_position.ids)],
                                'name': line.name or line.product_id.name,
                            }))

                    move_vals['invoice_line_ids'] = line_vals

                    new_move = self.env['account.move'].create(move_vals)
                    orders.write({'account_move': new_move.id, 'state': 'invoiced'})
                    new_move.sudo().with_company(orders[0].company_id).with_context(skip_invoice_sync=True)._post()
                    new_move.message_post_with_source(
                        'mail.message_origin_link',
                        render_values={'self': new_move, 'origin': orders},
                        subtype_xmlid='mail.mt_note',
                    )
                    invoices += new_move

                    for order in orders:
                        order._apply_invoice_payments(order.session_id.state == 'closed')

        return self.pos_order_ids.action_view_multiple_invoice(invoices=invoices)
