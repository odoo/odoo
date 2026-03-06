# Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    # Add index to res_model because filtering on it is a common use case
    res_model = fields.Char(index=True)
