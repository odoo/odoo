from odoo import _, fields, models, Command
from odoo.addons.web.controllers.utils import clean_action


class BankRecWidget(models.Model):
    _inherit = "bank.rec.widget"

    matched_sale_order_ids = fields.Many2many(
        comodel_name='sale.order',
        store=False,
    )

    def _action_trigger_matching_rules(self):
        # EXTENDS account_accountant
        matching = super()._action_trigger_matching_rules()
        if matching and matching.get('sale_orders'):
            self.matched_sale_order_ids = [Command.set(matching['sale_orders'].ids)]
        else:
            self.matched_sale_order_ids = [Command.clear()]
        return matching

    def _js_action_redirect_to_matched_sale_orders(self):
        self.ensure_one()
        sale_orders = self.matched_sale_order_ids._origin

        action = {
            'name': "Sale Orders",
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'context': {'create': False},
        }
        if len(sale_orders) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': sale_orders.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', sale_orders.ids)],
            })
        self.return_todo_command = clean_action(action, self.env)
