# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class ResPartnerBank(models.Model):

    _inherit = "res.partner.bank"

    l10n_ch_isrb_id_number = fields.Char(string="ISR-B Custmer ID", help="ISR-B Customer ID number for ISR. Used only when generating ISR reference through a bank. It is not necessary for standard ISR from Postfinance. The ISR reference will contains this number in the first digits.\ne.g. 999999 will generate 99 9999x xxxxx xxxxx xxxxx xxxxx xx references")
