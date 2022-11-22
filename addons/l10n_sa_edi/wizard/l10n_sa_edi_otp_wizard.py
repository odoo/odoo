from odoo import fields, models, _
from odoo.exceptions import UserError


class RequestZATCAOtp(models.TransientModel):
    _name = 'l10n_sa_edi.otp.wizard'
    _description = 'Request ZATCA OTP'

    l10n_sa_otp = fields.Char("OTP", copy=False, help="OTP required to get a CCSID. Can only be acquired through "
                                                      "the Fatoora portal.")

    def validate(self):
        if not self.l10n_sa_otp:
            raise UserError(_("You need to provide an OTP to be able to request a CCSID"))
        journal_id = self.env['account.journal'].browse(self.env.context.get('active_id'))
        if self.env.context.get('renew_pcsid'):
            return journal_id.l10n_sa_api_get_production_CSID(self.l10n_sa_otp)
        journal_id.l10n_sa_api_get_compliance_CSID(self.l10n_sa_otp)
