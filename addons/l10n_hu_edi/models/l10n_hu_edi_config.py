from odoo import fields, models


class L10nHuEdiConfig(models.Model):
    _name = "l10n_hu_edi.config"
    _description = "A company's l10n hu edi configuration"
    _inherit = ["mixin.company.config"]

    l10n_hu_tax_regime = fields.Selection(
        selection=[
            ("ie", "Individual Exemption"),
            ("ca", "Cash Accounting"),
            ("sb", "Small Business"),
        ],
        string="NAV Tax Regime",
    )
    l10n_hu_edi_server_mode = fields.Selection(
        selection=[
            ("production", "Production"),
            ("test", "Test"),
            ("demo", "Demo"),
        ],
        string="Server Mode",
        help="""
            - Production: Sends invoices to the NAV's production system.
            - Test: Sends invoices to the NAV's test system.
            - Demo: Mocks the NAV system (does not require credentials).
        """,
    )
    l10n_hu_edi_username = fields.Char(
        string="NAV Username",
        groups="base.group_system",
    )
    l10n_hu_edi_last_transaction_recovery = fields.Datetime(
        string="Last transaction recovery (in production mode)",
        default=lambda self: fields.Datetime.now(),
    )
