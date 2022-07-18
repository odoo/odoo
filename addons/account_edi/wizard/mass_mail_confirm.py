# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class MassMailConfirm(models.TransientModel):
    _name = "mass.mail.confirm"
    _description = "Confirm the sending of invoice woth edi in mass mail"

    test_fields = fields.Text('Hello', readonly=True)

    def action_confirm_sending(self):
        pass
