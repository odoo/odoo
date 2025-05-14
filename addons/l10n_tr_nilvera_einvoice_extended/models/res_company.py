from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_tr_nilvera_export_alias = fields.Char(
        string="Nilvera Export Alias",
        default="urn:mail:ihracatpk@gtb.gov.tr",
        groups="base.group_system",
    )
