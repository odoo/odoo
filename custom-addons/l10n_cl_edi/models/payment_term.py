# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class PaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    l10n_cl_sii_code = fields.Selection([
        ('1', '1: Cash payment'),
        ('2', '2: Credit'),
        ('3', '3: Other')], string='DTE SII Code', default='2')
