from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pl_edi_register = fields.Boolean("KSeF Integration Enabled", compute="_compute_l10n_pl_edi_register")
    l10n_pl_edi_certificate = fields.Many2one('certificate.certificate', "KSeF Certificate", store=True, groups='base.group_system')
    l10n_pl_edi_access_token = fields.Char("KSeF Token", readonly=True, copy=False, groups='base.group_system')
    l10n_pl_edi_refresh_token = fields.Char("KSeF Token Expiration", readonly=True, copy=False, groups='base.group_system')
    l10n_pl_edi_session_id = fields.Char("Reference number", readonly=True, groups='base.group_system')
    l10n_pl_edi_session_key = fields.Binary("Session key", readonly=True, groups='base.group_system')
    l10n_pl_edi_session_iv = fields.Binary("Session iv", readonly=True, groups='base.group_system')

    @api.depends("l10n_pl_edi_certificate")
    def _compute_l10n_pl_edi_register(self):
        for company in self:
            company.l10n_pl_edi_register = bool(company.l10n_pl_edi_certificate)
