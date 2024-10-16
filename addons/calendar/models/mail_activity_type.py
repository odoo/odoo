# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons import mail


class MailActivityType(mail.MailActivityType):

    category = fields.Selection(selection_add=[('meeting', 'Meeting')])
