from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pl_edi_certificate = fields.Many2one(
        string="KSeF Certificate",
        store=True,
        comodel_name='certificate.certificate',
    )
    l10n_pl_edi_register = fields.Boolean(default=False)
    l10n_pl_access_token = fields.Char(string="KSeF Token", readonly=True, copy=False, groups="base.group_system")
    l10n_pl_refresh_token = fields.Char(string="KSeF Token Expiration", readonly=True, copy=False, groups="base.group_system")
    l10n_pl_ksef_session_id = fields.Char(string="Reference number", readonly=True, groups="base.group_system")
    l10n_pl_ksef_session_key = fields.Binary(string="Session key", readonly=True, groups="base.group_system")
    l10n_pl_ksef_session_iv = fields.Binary(string="Session iv", readonly=True, groups="base.group_system")
