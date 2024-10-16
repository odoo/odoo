# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import web_editor


class HtmlFieldHistoryTest(models.Model, web_editor.HtmlFieldHistoryMixin):
    _description = "Test html_field_history Model"

    def _get_versioned_fields(self):
        return [
            HtmlFieldHistoryTest.versioned_field_1.name,
            HtmlFieldHistoryTest.versioned_field_2.name,
        ]

    versioned_field_1 = fields.Html(string="vf1")
    versioned_field_2 = fields.Html(string="vf2", sanitize=False)
