# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    model_id = fields.Many2one('ir.model', default=lambda self: self.env.context.get('object_id', False))

    # TODO: add constraint to prevent disabling / disapproving an email account used in a running campaign
