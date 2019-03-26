# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Lang(models.Model):
    _inherit = "res.lang"

    def _get_request_lang(self):
        for lang in self:
            lang.request_lang = lang.iso_code

    request_lang = fields.Char(compute='_get_request_lang', string='Request Lang code')
