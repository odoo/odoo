# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class IrModel(models.Model):
    _inherit = 'ir.model'
    _order = 'is_main_application DESC, model ASC'

    is_main_application = fields.Boolean(
        'Main Application', compute='_compute_is_main_application', store=True,
        help="Whether this model is considered as a main application and should be"
             "used and displayed preferentially in documents using models.")

    @api.depends('model')
    def _compute_is_main_application(self):
        MailThread = self.pool['mail.thread']
        for model in self.filtered(lambda rec: rec.model != 'mail.thread'):
            Model = self.pool.get(model.model)
            model.is_main_application = Model and issubclass(Model, MailThread)
