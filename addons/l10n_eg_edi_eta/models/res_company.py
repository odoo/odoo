from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"
    _CREDENTIAL_FIELDS = {
        "l10n_eg_client_secret": "l10n_eg_client_secret",
    }

    l10n_eg_client_identifier = fields.Char(
        string="ETA Client ID",
        groups="base.group_erp_manager",
    )
    l10n_eg_client_secret = fields.Char(
        string="ETA Secret",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        groups="base.group_erp_manager",
    )
    l10n_eg_production_env = fields.Boolean(string="In Production Environment")
    l10n_eg_invoicing_threshold = fields.Float(
        string="Invoicing Threshold",
        default=0.0,
        help="Threshold at which you are required to give the VAT number "
        "of the customer. ",
    )
