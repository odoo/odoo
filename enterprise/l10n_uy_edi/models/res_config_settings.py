import logging

from datetime import datetime, timedelta, timezone

from odoo import fields, models
from odoo.exceptions import UserError, AccessError
from odoo.addons.iap.tools import iap_tools
from odoo.addons.iap import InsufficientCreditError

_logger = logging.getLogger(__name__)

TEST_ENDPOINT = "https://l10n-uy-uruware.test.odoo.com/"
PROD_ENDPOINT = "https://l10n-uy-uruware.api.odoo.com/"


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_uy_edi_ucfe_env = fields.Selection(related="company_id.l10n_uy_edi_ucfe_env", readonly=False)
    l10n_uy_edi_ucfe_password = fields.Char(related="company_id.l10n_uy_edi_ucfe_password", readonly=False)
    l10n_uy_edi_ucfe_commerce_code = fields.Char(related="company_id.l10n_uy_edi_ucfe_commerce_code", readonly=False)
    l10n_uy_edi_ucfe_terminal_code = fields.Char(related="company_id.l10n_uy_edi_ucfe_terminal_code", readonly=False)

    def l10n_uy_edi_action_check_credentials(self):
        """ Make a ECHO test to UCFE to see if the server is running and that the environment
        params have been properly configured """
        error_msg = self.env["l10n_uy_edi.document"]._validate_credentials(self.company_id)
        if error_msg:
            _logger.info("Error Checking UCFE Provider Credentials: %s", error_msg)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "danger" if error_msg else "warning",
                "message": error_msg or self.env._("Everything is ok"),
                "next": {"type": "ir.actions.act_window_close"},
            }
        }

    def l10n_uy_edi_action_create_uruware_account(self):
        self.ensure_one()
        error = False
        in_test_mode = self.l10n_uy_edi_ucfe_env == "testing"
        notification_email = "your email"

        if not self.company_id.vat:
            raise UserError(self.env._('Please configure your company RUT first'))

        try:
            res = iap_tools.iap_jsonrpc(
                (TEST_ENDPOINT if in_test_mode else PROD_ENDPOINT) + "api/l10n_uy_reg_proxy/1/create_account",
                params={
                    "db_uuid": self.env["ir.config_parameter"].sudo().get_param("database.uuid", "FAKETESTID"),
                    "company": self.company_id.id,
                    "company_name": self.company_id.name,
                    "company_vat": self.company_id.vat,
                    "user_email": self.env.user.email,  # to be used as the email contact in test mode
                })
            if res.get("success") is not True:
                error = self.env._("Error connection to Odoo IAP to create UCFE Provider account")
                error_code = res.get('error')
                if error_code == 'error_invalid_dbuuid':
                    error = self.env._('Make sure you have a valid enterprise contract in this database. '
                              'If it is new, it might take some time for the system to recognize your contract. ')
                elif error_code == 'error_sending_mail':
                    error = self.env._('Your database is valid, but an error happened on our side. ')
                elif error_code == 'error_cooldown':
                    hours = res['hours']
                    minutes = res['minutes']
                    seconds = res['seconds']
                    error = self.env._("You can't send another request within 24 hours. "
                              "You will be able to send again in %(hours)s hours, %(minutes)s minutes, and %(seconds)s seconds.",
                              hours=hours, minutes=minutes, seconds=seconds)
                elif error_code == 'error_too_many_registrations':
                    error = self.env._("More than 5 registrations have been made within 24 hours in this database. "
                              "Please try again later.")
                elif error_code:
                    error += ":" + error_code
            else:  # res == {'success': True, 'email': <email_str>}
                notification_email = res["email"]

        except (UserError, InsufficientCreditError, AccessError) as exp:
            error = str(exp)

        if error:
            _logger.info("Error creating UCFE Provider account: %s", error)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "danger" if error else "warning",
                "message":
                    self.env._("Error creating the UCFE Provider account. Please contact support: ") + error if error else
                    self.env._("The account creating request has been successfully sent. "
                      "The credentials will be sent to %s. "
                      "Please check your email for more instructions",
                      notification_email),
                "next": {"type": "ir.actions.act_window_close"},
                "sticky": True,
            }
        }
