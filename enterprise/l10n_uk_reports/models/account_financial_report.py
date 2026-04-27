# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid

from odoo import models, _


class BritishGenericTaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_uk.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'British Tax Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        # If token, but no refresh_token, check if you got the refresh_token on the server first
        # That way, you can see immediately if your login was successful after logging in
        # and the label of the button will be correct
        if self.env.user.l10n_uk_user_token and not self.env.user.l10n_uk_hmrc_vat_token:
            self.env['hmrc.service']._login()
        button_name = _('Send to HMRC') if self.env.user.l10n_uk_hmrc_vat_token else _('Connect to HMRC')
        options['buttons'].append({'name': button_name, 'action': 'send_hmrc', 'sequence': 50, 'client_tag': 'send_hmrc_button_report', 'always_show': False})

    def send_hmrc(self, options):
        if not options.get('_running_export_test'):
            # do the login if there is no token for the current user yet.
            if not self.env.user.l10n_uk_hmrc_vat_token:
                return self.env['hmrc.service']._login()

            # Check obligations: should be logged in by now
            self.env['l10n_uk.vat.obligation'].import_vat_obligations(self.env.context['client_data'])

            # import_vat_obligations() removes the token if the user is not authorised when importing the obligations.
            # This can happen if the user switched companies then tried to send the report. Before the user had to
            # manually delete his tokens from the user tab but now they're automatically sent to the login page to
            # request a new token.
            if not self.env.user.l10n_uk_user_token:
                return self.env['hmrc.service']._login()

        # Show wizard when sending to HMRC
        context = self.env.context.copy()
        context.update({
            'options': options,
            'client_data': {
                **context.get('client_data', {}),
                'hmrc_gov_client_device_id': uuid.uuid4()
            }
        })
        view_id = self.env.ref('l10n_uk_reports.hmrc_send_wizard_form').id
        return {'type': 'ir.actions.act_window',
                'name': _('Send to HMRC'),
                'res_model': 'l10n_uk.hmrc.send.wizard',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                'context': context,
        }
