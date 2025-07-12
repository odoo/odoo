import json
import os
from datetime import datetime
from odoo import models

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_send_invoice_whatsapp(self):
        for invoice in self:
            message_data = {
                'phone': '+919490927230',
                'message': '📢 Rice Store App is Live!',
                'timestamp': str(datetime.now())
            }

            # Save the message to a file
            path = 'C:/odoo/send_queue.json'
            with open(path, 'w') as f:
                json.dump(message_data, f)