from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _prepare_mail_values_static(self):
        # Add 'source_mailing_id' (based on composer 'mass_mailing_id') propagation,
        # as part of outgoing message audit
        values = super()._prepare_mail_values_static()
        values['source_mailing_id'] = self.mass_mailing_id.id
        return values
