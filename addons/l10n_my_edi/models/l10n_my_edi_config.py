from odoo import api, fields, models


class L10nMyEdiConfig(models.Model):
    _name = "l10n_my_edi.config"
    _description = "A company's l10n my edi configuration"
    _inherit = ["mixin.company.config"]

    l10n_my_edi_proxy_user_id = fields.Many2one(
        comodel_name="account_edi_proxy_client.user",
        compute="_compute_l10n_my_edi_proxy_user_id",
    )
    l10n_my_identification_number_placeholder = fields.Char(
        compute="_compute_l10n_my_identification_number_placeholder"
    )
    l10n_my_edi_mode = fields.Selection(
        selection=[
            ("test", "Pre-Production"),
            ("prod", "Production"),
        ],
        # Nothing will happen until the user register, so it can be set by default.
        default="test",
    )
    l10n_my_edi_default_import_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Default import journal",
        domain="[('type', '=', 'purchase')]",
        help="The journal on which invoices imported from MyInvois will be booked. Leave empty to use the default purchase journal.",
    )

    @api.depends("company_id.account_edi_proxy_client_ids", "l10n_my_edi_mode")
    def _compute_l10n_my_edi_proxy_user_id(self):
        """Each company is expected to have at most one proxy user for malaysia for each mode.
        Thus, we can easily find said user.
        """
        for config in self:
            config.l10n_my_edi_proxy_user_id = (
                config.company_id.account_edi_proxy_client_ids.filtered(
                    lambda u, config=config: (
                        u.proxy_type == "l10n_my_edi"
                        and u.edi_mode == config.l10n_my_edi_mode
                    )
                )[:1]
            )

    @api.depends("company_id.l10n_my_identification_type")
    def _compute_l10n_my_identification_number_placeholder(self):
        """Computes a dynamic placeholder that depends on the selected type to help the user inputs their data.
        The placeholders have been taken from the MyInvois doc.
        """
        for config in self:
            identification_type = config.company_id.l10n_my_identification_type
            placeholder = "N/A"
            if identification_type == "NRIC":
                placeholder = "830503114923"
            elif identification_type == "BRN":
                placeholder = "202201234565"
            elif identification_type == "PASSPORT":
                placeholder = "A00000000"
            elif identification_type == "ARMY":
                placeholder = "830805134983"
            config.l10n_my_identification_number_placeholder = placeholder
