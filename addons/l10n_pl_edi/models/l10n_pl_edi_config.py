from odoo import api, fields, models


class L10nPlEdiConfig(models.Model):
    _name = "l10n_pl_edi.config"
    _description = "A company's l10n pl edi configuration"
    _inherit = ["mixin.company.config"]

    l10n_pl_edi_register = fields.Boolean(
        string="KSeF Integration Enabled",
        compute="_compute_l10n_pl_edi_register",
        compute_sudo=True,
    )
    l10n_pl_edi_certificate = fields.Many2one(
        comodel_name="certificate.certificate",
        string="KSeF Certificate",
        store=True,
        groups="base.group_system",
    )
    l10n_pl_edi_session_id = fields.Char(
        string="Reference number",
        readonly=True,
        groups="base.group_system",
    )
    l10n_pl_edi_session_key = fields.Binary(
        string="Session key",
        readonly=True,
        groups="base.group_system",
    )
    l10n_pl_edi_session_iv = fields.Binary(
        string="Session iv",
        readonly=True,
        groups="base.group_system",
    )

    @api.depends("l10n_pl_edi_certificate")
    def _compute_l10n_pl_edi_register(self):
        for company in self:
            company.l10n_pl_edi_register = bool(company.l10n_pl_edi_certificate)
