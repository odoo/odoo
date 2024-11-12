# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HtmlFieldHistoryTest(models.Model):
    _name = 'html.field.history.test'
    _description = "Test html_field_history Model"
    _inherit = ["html.field.history.mixin"]

    def _get_versioned_fields(self):
        return [
            HtmlFieldHistoryTest.versioned_field_1.name,
            HtmlFieldHistoryTest.versioned_field_2.name,
        ]

    versioned_field_1 = fields.Html(string="vf1")
    versioned_field_2 = fields.Html(string="vf2", sanitize=False)
