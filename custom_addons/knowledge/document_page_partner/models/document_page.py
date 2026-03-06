# Copyright 2015-24 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class DocumentPage(models.Model):
    _inherit = "document.page"

    partner_id = fields.Many2one("res.partner", "Partner", index=True)
