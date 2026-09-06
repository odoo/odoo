from odoo import fields, models
from odoo.tools import xml_translate, html_translate


class TranslatableModel(models.Model):
    _name = "translatable.cases"
    _description = "Translatable Cases"

    text = fields.Text(translate=True)
    xml = fields.Text(translate=xml_translate)
    html = fields.Html(sanitize=False, translate=True)
    structured_html = fields.Html(sanitize=True, translate=html_translate)
