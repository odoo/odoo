# coding: utf-8

from odoo import api, fields, models, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    sale_order_ids = fields.Many2many('sale.order', 'account_payment_sale_order_rel', 'account_payment_id', 'sale_order_id',
                                      compute='_compute_sale_order_ids', string='Sales Orders', readonly=True, store=True)
    sale_order_ids_nbr = fields.Integer(string='# of Sale Orders', compute='_compute_sale_orders_ids')

    @api.depends('sale_order_ids')
    def _compute_sale_orders_ids(self):
        '''Compute the number of payments for each invoice in self.'''
        self.check_access_rights('write')
        self.env['sale.order'].check_access_rights('read')

        self._cr.execute('''
            SELECT pay.id, COUNT(rel.account_payment_id)
            FROM account_payment pay
            LEFT JOIN account_payment_sale_order_rel rel ON pay.id = rel.sale_order_id
            WHERE pay.id IN %s
            GROUP BY pay.id
        ''', [tuple(self.ids)])
        records = dict((r.id, r) for r in self)
        for res in self._cr.fetchall():
            records[res[0]].sale_order_ids_nbr = res[1]

    @api.depends('invoice_ids')
    def _compute_sale_order_ids(self):
        ''' Compute the sale_order_ids ONLY if there are some invoices linked to the payment.
        This is required because some users could use the SO feature without invoicing and then,
        you could have 'so <- m2m -> inv <- m2m -> pay' and 'so <- m2m -> pay'.
        '''
        for pay in self.filtered(lambda p: p.invoice_ids):
            pay.sale_order_ids = [(6, 0, set(pay.invoice_ids.mapped('invoice_line_ids.sale_line_ids.order_id').ids))]

    @api.multi
    def action_view_sale_orders(self):
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Sales Orders'),
            'res_model': 'sale.order',
        }
        if self.sale_order_ids_nbr == 1:
            action.update({
                'res_id': self.sale_order_ids[0].id,
                'view_mode': 'form',
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', self.sale_order_ids.ids)],
            })
        return action
