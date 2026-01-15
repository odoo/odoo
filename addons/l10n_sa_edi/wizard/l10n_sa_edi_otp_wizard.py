from odoo import fields, models, _, api
from odoo.exceptions import UserError


class L10n_Sa_EdiOtpWizard(models.TransientModel):
    _name = 'l10n_sa_edi.otp.wizard'
    _description = 'Request ZATCA OTP'

    l10n_sa_renewal = fields.Boolean("PCSID Renewal",
                                     help="Used to decide whether we should call the PCSID renewal API or the CCSID API",
                                     default=False)
    l10n_sa_otp = fields.Char("OTP", copy=False, help="OTP required to get a CCSID. Can only be acquired through "
                                                      "the Fatoora portal.")
    journal_id = fields.Many2one('account.journal', default=lambda self: self.env.context.get('active_id'), required=True)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if self.env.company.l10n_sa_api_mode == 'sandbox':
            res['l10n_sa_otp'] = '123456' if self.l10n_sa_renewal else '123345'
        return res

    def validate(self):
        if not self.l10n_sa_otp:
            raise UserError(_("Please provide an OTP to complete the onboarding process"))
        if self.l10n_sa_renewal:
            return self.journal_id._l10n_sa_get_production_CSID(self.l10n_sa_otp)
        self.journal_id._l10n_sa_api_onboard_journal(self.l10n_sa_otp)
