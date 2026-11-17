from odoo import fields, models


class MailMail(models.Model):
    _inherit = 'mail.mail'

    block_open_tracking = fields.Boolean("Open Tracking Disabled")
    block_click_tracking = fields.Boolean("Click Tracking Disabled")

    def _is_open_tracking_allowed(self):
        return super()._is_open_tracking_allowed() and not self.block_open_tracking

    def _is_click_tracking_allowed(self):
        return super()._is_click_tracking_allowed() and not self.block_click_tracking
