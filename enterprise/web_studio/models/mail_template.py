# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailTemplate(models.Model):
    _name = 'mail.template'
    _description = 'Email Templates'
    _inherit = ['studio.mixin', 'mail.template']
