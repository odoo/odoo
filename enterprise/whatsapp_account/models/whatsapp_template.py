from odoo import models

class WhatsAppTemplate(models.Model):
    _inherit = 'whatsapp.template'

    def _get_sample_record(self):
        if self.model == 'account.move':
            return self.env[self.model].search([('move_type', '!=', 'entry')], limit=1)
        return super()._get_sample_record()
