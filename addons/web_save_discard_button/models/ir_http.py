# Copyright (C) 2023-TODAY Synconics Technologies Pvt. Ltd. (<http://www.synconics.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        modules = super()._get_translation_frontend_modules_name()
        return modules + ["web_save_discard_button"]
