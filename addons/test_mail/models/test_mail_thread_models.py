# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons import mail


class MailTestCc(models.Model, mail.MailThreadCc):
    _description = "Test Email CC Thread"

    name = fields.Char()
