import pytz

from odoo.tools import float_round
from odoo import api, models, fields, Command, _
from odoo.exceptions import UserError


class PosMakeInvoice(models.TransientModel):
    _name = 'pos.make.invoice'
    _description = 'Multiple order invoice creation'

    consolidated_billing = fields.Boolean(
        string="Consolidated Billing", default=True,
        help="Create one invoice for all orders related to same customer and same invoicing address"
    )
    count = fields.Integer(string="Order Count", compute='_compute_order_count')

    @api.depends('consolidated_billing')
    def _compute_order_count(self):
        for wizard in self:
            wizard.count = len(self.env.context.get('active_ids'))

    def _prepare_invoice_lines(self, orders):
        invoice_lines = []
        for order in orders:
            invoice_lines.extend(order._prepare_invoice_lines())
        return invoice_lines

    def _prepare_invoice_vals(self, orders):
        timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
        amount_total = sum(order.amount_total for order in orders)
        pos_refunded_invoice_ids = []
        for orderline in orders.mapped('lines'):
            if orderline.refunded_orderline_id and orderline.refunded_orderline_id.order_id.account_move:
                pos_refunded_invoice_ids.append(orderline.refunded_orderline_id.order_id.account_move.id)
        partner_id = orders.partner_id
        vals = {
            'invoice_origin': ', '.join(orders.mapped('name')),
            'pos_refunded_invoice_ids': pos_refunded_invoice_ids,
            'journal_id': orders[0].config_id.invoice_journal_id.id,
            'move_type': 'out_invoice' if amount_total >= 0 else 'out_refund',
            'partner_id': partner_id.address_get(['invoice'])['invoice'],
            'partner_bank_id': orders[0]._get_partner_bank_id(),
            'currency_id': orders[0].currency_id.id,
            'invoice_user_id': self.env.user.id,
            'invoice_date': fields.Datetime.now().astimezone(timezone).date(),
            'fiscal_position_id': orders[0].fiscal_position_id.id,
            'invoice_line_ids': self._prepare_invoice_lines(orders),
            'invoice_payment_term_id': partner_id.property_payment_term_id.id or False,
            'invoice_cash_rounding_id': orders[0].config_id.rounding_method.id
        }

        if any(order.refunded_order_id.account_move for order in orders):
            refunded_orders = orders.filtered(lambda o: o.refunded_order_id.account_move)
            vals['ref'] = _('Reversal of: %s', ','.join(refunded_orders.mapped('refunded_order_id.account_move.name')))
            vals['reversal_move_ids'] = refunded_orders.refunded_order_id.account_move.ids
        if any(order.floating_order_name for order in orders):
            vals.update({'narration': ', '.join(orders.filtered('floating_order_name').mapped('floating_order_name'))})

        return vals

    def create_invoices(self):
        self.ensure_one()
        if any(order_id for order_id in self.env['pos.order'].browse(self.env.context.get('active_ids')) if not order_id.partner_id):
            raise UserError(_("Some of the selected order(s) do not have customers assigned."))
        if any(order_id for order_id in self.env['pos.order'].browse(self.env.context.get('active_ids')) if order_id.state == 'draft'):
            raise UserError(_("Some of the order(s) are not paid."))
        if not any(order_id for order_id in self.env['pos.order'].browse(self.env.context.get('active_ids')) if order_id.invoice_status == 'to_invoice'):
            raise UserError(_(
                "Cannot create an invoice. No items are available to invoice.\n"
                "To resolve this issue, please ensure that there are some orders to be invoiced among the selected orders."
            ))
        pos_orders = self.env['pos.order'].browse(self.env.context.get('active_ids')).filtered(lambda o: o.invoice_status != 'invoiced')
        invoices = self.env['account.move']
        if not self.consolidated_billing:
            for order in pos_orders:
                invoices |= order.action_pos_order_invoice()
        else:
            for config in pos_orders.mapped('config_id'):
                orders_by_config = pos_orders.filtered(lambda o: o.config_id == config)
                for partner in orders_by_config.partner_id:
                    orders_by_partner = orders_by_config.filtered(lambda o: o.partner_id == partner)
                    for fiscal_position in orders_by_partner.fiscal_position_id:
                        orders_with_fiscal = orders_by_partner.filtered(lambda o: o.fiscal_position_id == fiscal_position)
                        if orders_with_fiscal:
                            inv = self.prepare_invoices(orders_with_fiscal)
                            invoices |= inv
                    order_wo_fiscal = orders_by_partner.filtered(lambda o: not o.fiscal_position_id)
                    if order_wo_fiscal:
                        inv2 = self.prepare_invoices(order_wo_fiscal)
                        invoices |= inv2
        if pos_orders:
            return pos_orders.action_view_multiple_invoice(invoices=invoices)

    def prepare_invoices(self, orders):
        invoices = self.env['account.move']
        move_vals = self._prepare_invoice_vals(orders)
        move = self.env['account.move'].with_context(default_move_type=move_vals['move_type']).create(move_vals)
        orders.write({'account_move': move.id, 'state': 'invoiced'})
        move.message_post_with_source(
            'mail.message_origin_link',
            render_values={'self': move, 'origin': orders},
            subtype_xmlid='mail.mt_note',
        )
        move.write({'payment_state': 'paid'})
        invoices |= move

        return invoices
