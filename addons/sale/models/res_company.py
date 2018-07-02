# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    sale_note = fields.Text(string='Default Terms and Conditions', translate=True)
    portal_confirmation_sign = fields.Boolean(string='Digital Signature')
    portal_confirmation_pay = fields.Boolean(string='Electronic Payment')
