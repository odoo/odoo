from odoo import fields, models


class L10nSaEdiConfig(models.Model):
    _name = "l10n_sa_edi.config"
    _description = "A company's l10n sa edi configuration"
    _inherit = ["mixin.company.config"]

    l10n_sa_private_key_id = fields.Many2one(
        comodel_name="certificate.key",
        string="ZATCA Private key",
        copy=False,
        domain=[("public", "=", False)],
        help="The private key used to generate the CSR and obtain certificates",
    )
    l10n_sa_api_mode = fields.Selection(
        selection=[
            ("sandbox", "Sandbox"),
            ("preprod", "Simulation (Pre-Production)"),
            ("prod", "Production"),
        ],
        default="sandbox",
        copy=False,
        required=True,
        help="Specifies which API the system should use",
    )
    l10n_sa_edi_is_production = fields.Boolean(
        string="Is Production",
        copy=False,
    )
