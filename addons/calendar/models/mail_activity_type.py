# -*- coding: utf-8 -*-
from odoo.addons import mail
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class MailActivityType(models.Model, mail.MailActivityType):

    category = fields.Selection(selection_add=[('meeting', 'Meeting')])
