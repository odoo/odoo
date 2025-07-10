# -*- coding: utf-8 -*-

from odoo import models

class PosConfig(models.Model):
    _inherit = 'pos.config'


    def get_additional_notify_message(self):
        message = super().get_additional_notify_message()
        return {
            **message,
            'coupons': self.env.context.get("coupons", {})
        }
