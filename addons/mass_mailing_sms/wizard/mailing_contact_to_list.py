# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailingContactToList(models.TransientModel):
    _inherit = 'mailing.contact.to.list'

    def _get_no_contact_details_message(self, count):
        return self.env._("%(count)s ignored (no email/phone)", count=count)
