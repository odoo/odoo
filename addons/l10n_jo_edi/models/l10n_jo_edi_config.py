from odoo import fields, models


class L10nJoEdiConfig(models.Model):
    _name = "l10n_jo_edi.config"
    _description = "A company's l10n jo edi configuration"
    _inherit = ["mixin.company.config"]

    l10n_jo_edi_sequence_income_source = fields.Char(
        string="JoFotara Sequence of Income Source"
    )
    l10n_jo_edi_client_identifier = fields.Char(
        string="JoFotara Client ID",
        groups="base.group_system",
    )
    l10n_jo_edi_taxpayer_type = fields.Selection(
        selection=[
            ("income", "Unregistered in the sales tax"),
            ("sales", "Registered in the sales tax"),
            ("special", "Registered in the special sales tax"),
        ],
        string="JoFotara Taxpayer Type",
        default="sales",
    )
    l10n_jo_edi_demo_mode = fields.Boolean(string="JoFotara Demo Mode")
