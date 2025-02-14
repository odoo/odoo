from odoo import models, fields, _
from odoo.exceptions import UserError


class PosMakeInvoice(models.TransientModel):
    _name = 'pos.make.invoice'
    _description = 'Multiple order invoice creation'

    consolidated_billing = fields.Boolean(
        string="Consolidated Billing", default=True,
        help="Create one invoice for all orders related to same customer and same invoicing address"
    )
    count = fields.Integer(string="Order Count", compute='_compute_order_count')

    def _compute_order_count(self):
        for wizard in self:
            wizard.count = len(self.env.context.get('active_ids', []))

    def action_create_invoices(self):
        self.ensure_one()
        selected_orders = self.env['pos.order'].browse(self.env.context.get('active_ids'))
        is_single_order = len(selected_orders) == 1

        uninvoiceable_orders = selected_orders.filtered(lambda o: o.invoice_status != 'to_invoice' or o.state == 'draft' or o.state == 'cancel' )
        if uninvoiceable_orders:
            order_names = "\n".join(uninvoiceable_orders.mapped('pos_reference'))
            raise UserError(_(
                "Unable to create consolidated invoice/s because the following orders can't be invoiced.\n\n%s",
                order_names
            ))

        invalid_refund_orders = selected_orders.filtered(lambda o: o.refunded_order_id.account_move)
        if (not is_single_order) and invalid_refund_orders:
            # Normally it can't be encountered because when paying a refund order,
            # if the original order is invoiced, the refund order is required by the UI to be invoiced.
            order_names = "\n".join([f"{o.name} ({o.pos_reference})" for o in invalid_refund_orders])
            raise UserError(_("The following refund orders can't be part of a consolidated invoice because they refunded invoiced orders. Each refund order should be handled separately.\n\n%s", order_names))

        invoices = self.env['account.move']

        if not self.consolidated_billing or len(selected_orders) == 1:
            for order in selected_orders:
                invoices |= order._generate_pos_order_invoice()
        else:
            configs = selected_orders.config_id
            partners = selected_orders.partner_id
            some_order_has_no_partner = any(not o.partner_id for o in selected_orders)
            if len(configs) == 1 and len(partners) == 1 and some_order_has_no_partner:
                # When all the orders belong to one config and there is only one customer but some orders have no partner,
                # we can proceed but we ask the user if we proceed by setting that one customer to all the orders.
                return {
                    'name': _('Warning'),
                    'view_mode': 'form',
                    'view_id': self.env.ref('point_of_sale.view_confirm_action_wizard').id,
                    'res_model': 'pos.confirmation.wizard',
                    'target': 'new',
                    'type': 'ir.actions.act_window',
                    'context': {'orders': selected_orders.ids, 'dialog_size': 'medium'},
                }

            grouped_orders = []
            for config, config_orders in selected_orders.grouped('config_id').items():
                for partner, partner_orders in config_orders.grouped('partner_id').items():
                    if not partner:
                        raise UserError(_("Kindly ensure that each order contains a customer."))

                    for fiscal_position, fiscal_position_orders in partner_orders.grouped('fiscal_position_id').items():
                        grouped_orders.append(((config, partner, fiscal_position), fiscal_position_orders))

            for _key, orders in grouped_orders:
                invoices |= orders._generate_pos_order_invoice()

        if invoices:
            return selected_orders.action_view_invoice()
