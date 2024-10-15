# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import rating, portal


class MailThread(portal.MailThread, rating.MailThread):

    def _get_allowed_message_post_params(self):
        return super()._get_allowed_message_post_params() | {"rating_value"}
