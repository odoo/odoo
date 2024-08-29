# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import mail

from odoo import models


class MailThread(models.AbstractModel, mail.MailThread):

    def _get_allowed_message_post_params(self):
        return super()._get_allowed_message_post_params() | {"rating_value"}
