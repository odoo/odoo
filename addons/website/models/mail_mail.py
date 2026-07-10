# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailMail(models.Model):
    _inherit = ['mail.mail']

    def _get_form_signed_fields(self):
        # Note: `email_bcc` is not a field; it is an exception
        return super()._get_form_signed_fields() | {'email_to', 'email_cc', 'email_bcc'}
