# -*- coding: utf-8 -*-
from odoo.addons import base
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel, base.ResConfigSettings):

    stock_move_sms_validation = fields.Boolean(
        related='company_id.stock_move_sms_validation',
        string='SMS Validation with stock move', readonly=False)
    stock_sms_confirmation_template_id = fields.Many2one(
        related='company_id.stock_sms_confirmation_template_id', readonly=False)
