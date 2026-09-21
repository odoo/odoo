from odoo import fields, models


class L10nTrNilveraEinvoiceExtendedConfig(models.Model):
    _name = "l10n_tr_nilvera_einvoice_extended.config"
    _description = "A company's l10n tr nilvera einvoice extended configuration"
    _inherit = ["mixin.company.config"]

    l10n_tr_nilvera_export_alias = fields.Char(
        string="Nilvera Export Alias",
        default="urn:mail:ihracatpk@gtb.gov.tr",
        groups="base.group_system",
    )
