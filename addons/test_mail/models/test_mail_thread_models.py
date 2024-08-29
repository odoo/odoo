# -*- coding: utf-8 -*-
from odoo.addons import mail
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailTestCC(models.Model, mail.MailThreadCc):
    _description = "Test Email CC Thread"

    name = fields.Char()
