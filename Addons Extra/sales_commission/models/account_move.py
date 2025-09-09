from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    def write(self, vals):
        # We are interested in the change of payment_state to 'paid'
        paid_invoices = self.filtered(lambda move: move.move_type == 'out_invoice' and move.payment_state != 'paid' and vals.get('payment_state') == 'paid')

        res = super(AccountMove, self).write(vals)

        for invoice in paid_invoices:
            # Find the related sales order
            sale_orders = invoice.invoice_line_ids.sale_line_ids.order_id
            for so in sale_orders:
                if so.user_id and so.amount_total:
                    salesperson = so.user_id

                    # Find salesperson's partner
                    partner = salesperson.partner_id
                    if not partner:
                        continue # Or create one? For now, we skip.

                    # Calculate commission (10% for now)
                    commission_amount = so.amount_total * 0.10

                    # Find a suitable expense account for commission
                    # Let's search for an account for commissions. If not found, we can't proceed.
                    # This should ideally be a configurable setting.
                    commission_account = self.env['account.account'].search([('name', 'ilike', 'Commissions'), ('company_id', '=', so.company_id.id)], limit=1)
                    if not commission_account:
                        # As a fallback, search for any expense account
                        commission_account = self.env['account.account'].search([
                            ('account_type', '=', 'expense'),
                            ('company_id', '=', so.company_id.id)
                        ], limit=1)

                    if not commission_account:
                        continue # Cannot create bill without an account

                    # Create vendor bill
                    self.env['account.move'].create({
                        'move_type': 'in_invoice',
                        'partner_id': partner.id,
                        'invoice_date': fields.Date.context_today(self),
                        'invoice_line_ids': [(0, 0, {
                            'name': f'Commission for sale {so.name}',
                            'account_id': commission_account.id,
                            'price_unit': commission_amount,
                            'quantity': 1,
                        })],
                    })
        return res
