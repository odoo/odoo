from odoo import fields, models


class L10nGrEdiConfig(models.Model):
    _name = "l10n_gr_edi.config"
    _description = "A company's l10n gr edi configuration"
    _inherit = ["mixin.company.config"]

    l10n_gr_edi_aade_id = fields.Char(string="AADE User ID")
    l10n_gr_edi_test_env = fields.Boolean(
        string="Greece Test Environment",
        default=True,
        help="Enable test environments with credentials obtained from https://mydata-dev-register.azurewebsites.net/",
    )
