# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import SUPERUSER_ID, models


_logger = logging.getLogger(__name__)

INT_PHONE_NUMBER_FORMAT_REGEX = r'^\+[^+]+$'


class SDDMandate(models.Model):
    _inherit = 'sdd.mandate'

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') in ['closed', 'revoked']:
            linked_tokens = self.env['payment.token'].search([('sdd_mandate_id', 'in', self.ids)])
            linked_tokens.sudo().active = False  # In sudo mode to write on payment.token.
        return res

    def _confirm(self):
        """ Confirm the customer's ownership of the SEPA Direct Debit mandate. """
        template = self.env.ref('payment_sepa_direct_debit.mail_template_sepa_notify_validation')
        self.write({'state': 'active'})
        template.with_user(SUPERUSER_ID).send_mail(self.id)
