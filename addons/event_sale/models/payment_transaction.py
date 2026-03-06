from odoo import models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _post_process(self):
        confirmed_txs = self.filtered(lambda tx: tx.state in ['authorized', 'done'] and tx.operation != 'validation')

        for tx in confirmed_txs:
            ticket_qtys = {}
            for line in tx.sale_order_ids.order_line:
                if hasattr(line, 'event_ticket_id') and line.event_ticket_id:
                    ticket_qtys[line.event_ticket_id] = ticket_qtys.get(line.event_ticket_id, 0) + line.product_uom_qty

            if ticket_qtys:
                tickets = self.env['event.event.ticket'].browse([t.id for t in ticket_qtys])
                tickets._lock_and_check_availability(ticket_qtys)

        return super()._post_process()
