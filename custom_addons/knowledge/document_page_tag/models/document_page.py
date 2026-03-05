# Copyright 2015-2018 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class DocumentPage(models.Model):
    _inherit = "document.page"

    tag_ids = fields.Many2many("document.page.tag", string="Keywords")
