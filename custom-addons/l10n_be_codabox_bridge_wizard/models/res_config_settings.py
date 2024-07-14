# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
from odoo import fields, models, _
from odoo.tools import frozendict
from odoo.exceptions import UserError
from odoo.addons.l10n_be_codabox.const import get_error_msg


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_be_codabox_show_iap_token = fields.Boolean(related="company_id.l10n_be_codabox_show_iap_token")

    def l10n_be_codabox_refresh_connection_status(self):
        self.ensure_one()
        error = self.company_id._l10n_be_codabox_refresh_connection_status()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'danger' if not self.l10n_be_codabox_is_connected else 'success',
                'title': _('Error') if not self.l10n_be_codabox_is_connected else _('Success'),
                'message': error if not self.l10n_be_codabox_is_connected else _('CodaBox connection established.'),
                'next': {
                    'type': 'ir.actions.act_window_close'
                },
            },
        }

    def l10n_be_codabox_open_connection_wizard(self):
        self.ensure_one()
        try:
            params = self.company_id._l10n_be_codabox_get_iap_common_params()
            params["iap_token"] = self.company_id.l10n_be_codabox_iap_token
            result = self.company_id._l10_be_codabox_call_iap_route("check_status", params)
            self.company_id.l10n_be_codabox_is_connected = result.get("connection_exists") and result.get("is_fidu_consent_valid")
            wizard = self.env['l10n_be_codabox.connection.wizard'].create({
                'company_id': self.company_id.id,
                'connection_exists': result.get("connection_exists"),
                'is_fidu_consent_valid': result.get("is_fidu_consent_valid"),
                'nb_connections': result.get("fidu_number_of_connections"),
            })
            return self.company_id._l10n_be_codabox_return_wizard(
                name=_('Manage Connection'),
                view_id=self.env.ref('l10n_be_codabox_bridge_wizard.connection_wizard_view').id,
                res_model='l10n_be_codabox.connection.wizard',
                res_id=wizard.id,
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise UserError(get_error_msg({"type": "error_connecting_iap"}))

    def l10n_be_codabox_open_soda_mapping(self):
        self.ensure_one()
        journal = self.l10n_be_codabox_soda_journal or self.env['account.journal'].search([('type', '=', 'general')], limit=1)
        wizard = self.env['soda.import.wizard'].create({
            'soda_files': {},
            'soda_code_to_name_mapping': {},
            'company_id': self.company_id.id,
            'journal_id': journal.id,  # Required by the wizard but not used
        })
        res = self.company_id._l10n_be_codabox_return_wizard(
            name=_('SODA Mapping'),
            view_id=self.env.ref('l10n_be_codabox_bridge.soda_import_wizard_view_form_codabox').id,
            res_model='soda.import.wizard',
            res_id=wizard.id,
        )
        res['context'] = frozendict(**res['context'], soda_mapping_save_only=True)
        return res
