# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
import requests
from odoo import models, fields, _, api
from odoo.exceptions import UserError
from odoo.addons.l10n_be_codabox.const import get_error_msg, get_iap_endpoint


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_be_codabox_iap_token = fields.Char(readonly=True, groups="base.group_system")
    l10n_be_codabox_is_connected = fields.Boolean(string="CodaBox Is Connected", compute="_compute_l10n_be_codabox_is_connected", store=True)
    l10n_be_codabox_show_iap_token = fields.Boolean()

    def _l10n_be_codabox_get_iap_common_params(self):
        self._l10n_be_codabox_verify_prerequisites()
        return {
            "db_uuid": self.env["ir.config_parameter"].sudo().get_param("database.uuid"),
            "company_vat": re.sub("[^0-9]", "", self.vat or self.company_registry),
            "fidu_vat": re.sub("[^0-9]", "", self.l10n_be_codabox_fiduciary_vat),
        }

    @api.model
    def _l10n_be_codabox_return_wizard(self, name, view_id, res_model, res_id):
        return {
            'name': name,
            'view_id': view_id,
            'res_model': res_model,
            'res_id': res_id,
            'context': self.env.context,
            'type': 'ir.actions.act_window',
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'new',
        }

    @api.model
    def _l10_be_codabox_call_iap_route(self, route, params):
        response = requests.post(f"{get_iap_endpoint(self.env)}/{route}", json={"params": params}, timeout=10)
        result = response.json().get("result", {})
        error = result.get("error")
        if error:
            raise UserError(get_error_msg(error))
        return result

    def _l10n_be_codabox_verify_prerequisites(self):
        self.check_access_rule('write')
        self.check_access_rights('write')
        self.ensure_one()
        if not self.vat and not self.company_registry:
            raise UserError(_("The company VAT number or ID is not set."))
        if not self.l10n_be_codabox_fiduciary_vat:
            raise UserError(_("The feature is restricted to Accounting Firms."))

    @api.depends("l10n_be_codabox_iap_token")
    def _compute_l10n_be_codabox_is_connected(self):
        for company in self:
            if company.l10n_be_codabox_iap_token:
                company._l10n_be_codabox_refresh_connection_status()
            else:
                company.l10n_be_codabox_is_connected = False

    def _l10n_be_codabox_refresh_connection_status(self):
        """
        Refresh the connection status of the company with CodaBox.
        :return: error message (if empty, it means there is no error)
        """
        error = ""
        try:
            params = self._l10n_be_codabox_get_iap_common_params()
            params["iap_token"] = self.l10n_be_codabox_iap_token
            result = self._l10_be_codabox_call_iap_route("check_status", params)
            if not result.get("connection_exists"):
                self.l10n_be_codabox_is_connected = False
                error = get_error_msg({"type": "error_connection_not_found"})
            else:
                self.l10n_be_codabox_is_connected = result.get("is_fidu_consent_valid", False)
                if not self.l10n_be_codabox_is_connected:
                    error = _("CodaBox consent is not valid. Please reconnect.")
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            error = get_error_msg({"type": "error_connecting_iap"})
        except UserError as e:
            self.env.cr.rollback()
            self.l10n_be_codabox_is_connected = False
            self.env.cr.commit()
            error = str(e)
        return error
