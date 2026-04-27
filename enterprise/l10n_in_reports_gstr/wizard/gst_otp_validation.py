# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from odoo import fields, models, _
from odoo.exceptions import RedirectWarning, UserError


class GstOtpValidation(models.TransientModel):
    _name = 'l10n_in.gst.otp.validation'
    _description = 'GST portal validation.'

    company_id = fields.Many2one('res.company', string="Company Name")
    gst_otp = fields.Char("OTP", copy=False)
    gst_token = fields.Char("GST Token", readonly=True)

    def check_gst_number(self):
        if not self.company_id.vat:
            action = {
                "view_mode": "form",
                "res_model": "res.company",
                "type": "ir.actions.act_window",
                "res_id": self.company_id.id,
                "views": [[self.env.ref("base.view_company_form").id, "form"]],
            }
            raise RedirectWarning(_("Please enter a GST number in company."), action, _('Go to Company'))

    def _l10n_in_reports_gstr_check_gst_token(self):
        """Check if another company with the same GST number has a valid GST token.

        If found, raises a RedirectWarning to guide the user to the Tax Units view.
        """

        count = self.env['res.company'].sudo().search_count([
            ('id', '!=', self.company_id.id),
            ('vat', '=', self.company_id.vat),
            ('l10n_in_gstr_gst_token_validity', '>', fields.Datetime.now()),
        ], limit=1)
        if count < 1:
            return
        message = _(
            "Another company is already using this GST number with "
            "a valid GST token. To proceed, make sure this company is "
            "part of a Tax Unit.",
        )
        action = self.env.ref('account_reports.action_view_tax_units')
        raise RedirectWarning(message, action.id, _('Go to Tax units'))

    def gst_send_otp(self):
        self.check_gst_number()
        self._l10n_in_reports_gstr_check_gst_token()
        response = self.env["l10n_in.gst.return.period"]._otp_request(self.company_id)
        if response.get('error'):
            error_message = "\n".join(["[%s] %s" % (error.get('code'), error.get('message')) for error in response.get("error", {})])
            raise UserError(error_message)
        else:
            self.gst_token = response.get("txn")
        form = self.env.ref("l10n_in_reports_gstr.view_validate_otp_gstr")
        return {
            "name": _("OTP Request"),
            "type": "ir.actions.act_window",
            "res_model": "l10n_in.gst.otp.validation",
            "res_id": self.id,
            "views": [[form.id, "form"]],
            "target": "new",
            "context": self._context,
        }

    def validate_otp(self):
        response = self.env["l10n_in.gst.return.period"]._otp_auth_request(
            company=self.company_id, transaction=self.gst_token, otp=self.gst_otp)
        if response.get('error'):
            error_codes = [e.get('code') for e in response["error"]]
            if 'AUTH4033' in error_codes:
                raise UserError(_("Invalid OTP"))
            message = "\n".join(["[%s] %s" % (e.get('code'), e.get('message')) for e in response["error"]])
            raise UserError(_('%s', message))
        self.company_id.sudo().write({
            "l10n_in_gstr_gst_token": self.gst_token,
            "l10n_in_gstr_gst_token_validity": fields.Datetime.now() + timedelta(hours=6)
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'sticky': False,
                'message': _("API credentials validated successfully"),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def validate_otp_and_do_next_action(self):
        if not (self.gst_otp and self.gst_otp.isdigit() and len(self.gst_otp) == 6):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _("Invalid OTP. Please enter a valid 6-digit OTP"),
                }
            }
        response = self.validate_otp()
        next_gst_action = self._context.get('next_gst_action')
        active_model = self._context.get('active_model')
        if next_gst_action and active_model:
            return_period = self.env[active_model].browse(self._context.get('active_id'))
            if next_gst_action == "send_gstr1":
                return_period.button_send_gstr1()
            elif next_gst_action == "gstr1_status":
                return_period.button_check_gstr1_status()
            elif next_gst_action == "fetch_gstr2b":
                return_period.action_get_gstr2b_data()
            elif next_gst_action == 'fetch_irn_from_account_move':
                response_message = return_period.l10n_in_update_move_using_irn()
                response['params']['next'] = response_message
            elif next_gst_action == 'fetch_irn':
                response_message = return_period.action_get_irn_data()
                response['params']['next'] = response_message
        return response
