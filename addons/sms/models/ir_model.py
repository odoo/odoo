# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class IrModel(models.Model):
    _inherit = 'ir.model'

    is_mail_thread_sms = fields.Boolean(
        string="Mail Thread SMS", default=False,
        store=False, compute='_compute_is_mail_thread_sms', search='_search_is_mail_thread_sms',
        help="Whether this model supports messages and notifications through SMS",
    )

    @api.depends('is_mail_thread')
    def _compute_is_mail_thread_sms(self):
        for model in self:
            if model.is_mail_thread:
                ModelObject = self.env[model.model]
                potential_fields = ModelObject._sms_get_number_fields() + ModelObject._sms_get_partner_fields()
                if any(fname in ModelObject._fields for fname in potential_fields):
                    model.is_mail_thread_sms = True
                    continue
            model.is_mail_thread_sms = False

    def _search_is_mail_thread_sms(self, operator, value):
        thread_models = self.search([('is_mail_thread', '=', True)])
        valid_models = self.env['ir.model']
        for model in thread_models:
            ModelObject = self.env[model.model]
            potential_fields = ModelObject._sms_get_number_fields() + ModelObject._sms_get_partner_fields()
            if any(fname in ModelObject._fields for fname in potential_fields):
                valid_models |= model

        search_sms = (operator == '=' and value) or (operator == '!=' and not value)
        if search_sms:
            return [('id', 'in', valid_models.ids)]
        return [('id', 'not in', valid_models.ids)]
