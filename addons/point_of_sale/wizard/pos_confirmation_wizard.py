from odoo import models, fields, api, _

class PosConfirmationWizard(models.TransientModel):
    _name = 'pos.confirmation.wizard'
    _description = 'Confirmation Wizard'

    def get_selected_orders(self):
        selected_orders = self.env.context.get('orders')
        return self.env['pos.order'].browse(selected_orders)

    def _default_message(self):
        selected_orders = self.get_selected_orders()
        customer_name = selected_orders.partner_id.name
        message = _("It seems that the POS order(s) %(order_ref)s do not have a customer.\n\nWould you like to set %(customer_name)s as the customer for the selected POS order(s)?", order_ref= ', '.join(selected_orders.filtered(lambda o: not o.partner_id).mapped('name')), customer_name=customer_name)
        return message

    message = fields.Text(default=_default_message, readonly=True)

    def action_confirm(self):
        selected_orders = self.get_selected_orders()
        selected_orders.write({'partner_id': selected_orders.partner_id.id})
        return {
            'name': _('Create Invoice(s)'),
            'view_mode': 'form',
            'view_id': self.env.ref('point_of_sale.view_pos_make_invoice').id,
            'res_model': 'pos.make.invoice',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'active_ids': selected_orders.ids},
        }

