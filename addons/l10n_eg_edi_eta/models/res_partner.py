from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_eg_building_no = fields.Char(string="Building No.")

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ["l10n_eg_building_no"]

    def _address_fields(self):
        return super()._address_fields() + ["l10n_eg_building_no"]
