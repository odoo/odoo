from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------

    l10n_pk_edi_enable = fields.Boolean(
        related='company_id.l10n_pk_edi_enable',
        readonly=False,
    )
    l10n_pk_edi_test_environment = fields.Boolean(
        related='company_id.l10n_pk_edi_test_environment',
        readonly=False,
    )
    l10n_pk_edi_auth_token = fields.Char(
        related='company_id.l10n_pk_edi_auth_token',
        readonly=False,
    )
