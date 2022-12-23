# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError


class AccountInvoiceSend(models.TransientModel):
    _inherit = 'account.invoice.send'

    def send_and_print_action(self):
        self.ensure_one()
        if any((i.country_id.code == 'SA' and not (i._is_ready_to_be_sent() or i.pos_order_ids)) for i in
               self.invoice_ids):
            raise UserError(_("Cannot send/print a standard Invoice to a customer unless it has been cleared by ZATCA"))
        return super().send_and_print_action()
