# -*- coding: utf-8 -*-
from openerp import fields, models

class HtmlFormSnippetAction(models.Model):

    _name = "html.form.snippet.action"
    _description = "HTML Form Snippet Action"

    name = fields.Char(string="Action Name", required=True)
    action_model = fields.Char(string="Action Model", required=True)
