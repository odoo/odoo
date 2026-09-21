from odoo import api, models
from odoo.fields import Domain


class Company(models.Model):
    _name = "res.company"
    _inherit = ["res.company", "mixin.document.default.folder"]

    @api.model
    def _get_domain_used_folder_ids(self, folder_ids: list[int]) -> Domain:
        return Domain.FALSE
