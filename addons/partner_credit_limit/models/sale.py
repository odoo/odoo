# See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def check_limit(self):
        self.ensure_one()
        moveline_obj = self.env['account.move.line']
        partner = self.partner_id
        user_id = self.env['res.users'].search([
            ('partner_id', '=', partner.id)], limit=1)
        if user_id and not user_id.has_group('base.group_portal') or not \
                user_id:
            movelines = moveline_obj.search(
                [('partner_id', '=', partner.id),
                 ('account_id.account_type', 'in',
                  ['Receivable', 'Payable']),
                 ('parent_state', '!=', 'cancel')]
            )
            confirm_sale_order = self.search(
                [('partner_id', '=', partner.id),
                 ('state', '=', 'sale'),
                 ('invoice_status', '!=', 'invoiced')])
            amount_total = sum(confirm_sale_order.mapped('amount_total'))

            credit = sum(movelines.mapped('credit'))
            debit = sum(movelines.mapped('debit'))

            partner_credit_limit = (debit + amount_total) - credit
            available_credit_limit = round(
                partner.credit_limit - partner_credit_limit, 2)
            if partner_credit_limit > partner.credit_limit and \
                    partner.credit_limit > 0.0:
                if not partner.over_credit:
                    msg = 'Your available credit limit' \
                              ' Amount = %s \nCheck "%s" Accounts or Credit ' \
                          'Limits.' % (available_credit_limit,
                                       self.partner_id.name)
                    raise UserError(_('You can not confirm Sale '
                                      'Order. \n' + msg))
            return True

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            order.check_limit()
        return res

    @api.constrains('amount_total')
    def check_amount(self):
        for order in self:
            order.check_limit()

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        if res.partner_id.credit_limit > 0.0 and \
                not res.partner_id.over_credit:
            res.check_limit()
        return res
