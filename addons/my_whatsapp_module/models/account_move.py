from odoo import models

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_send_invoice_whatsapp(self):
        for record in self:
            # Replace this with your actual WhatsApp logic
            message = f"Invoice {record.name} sent via WhatsApp!"
            print(message)