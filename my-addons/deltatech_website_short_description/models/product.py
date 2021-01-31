# ©  2015-2020 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import fields, models
from odoo.tools.translate import html_translate


class ProductTemplate(models.Model):

    _inherit = "product.template"

    website_short_description = fields.Html(
        "Short description for the website", sanitize_attributes=False, translate=html_translate
    )
