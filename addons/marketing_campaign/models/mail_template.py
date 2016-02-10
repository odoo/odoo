# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"
    model_id = fields.Many2one(
        default=lambda self: self.env.context.get('object_id'))
