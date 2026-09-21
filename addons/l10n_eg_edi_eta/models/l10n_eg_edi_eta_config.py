from odoo import fields, models


class L10nEgEdiEtaConfig(models.Model):
    _name = "l10n_eg_edi_eta.config"
    _description = "A company's l10n eg edi eta configuration"
    _inherit = ["mixin.company.config"]

    l10n_eg_client_identifier = fields.Char(
        string="ETA Client ID",
        groups="base.group_erp_manager",
    )
    l10n_eg_production_env = fields.Boolean(string="In Production Environment")
    l10n_eg_invoicing_threshold = fields.Float(
        string="Invoicing Threshold",
        default=0.0,
        help="Threshold at which you are required to give the VAT number "
        "of the customer. ",
    )
