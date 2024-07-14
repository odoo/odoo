# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, _, api
from odoo.addons.l10n_be_codabox.const import raise_deprecated


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_be_codabox_iap_token = fields.Char(readonly=True, groups="base.group_system")
    l10n_be_codabox_is_connected = fields.Boolean(string="CodaBox Is Connected", compute="_compute_l10n_be_codabox_is_connected", store=True)
    l10n_be_codabox_show_iap_token = fields.Boolean()

    @api.model
    def _l10_be_codabox_call_iap_route(self, route, params):
        raise_deprecated(self.env)

    def _l10n_be_codabox_verify_prerequisites(self):
        raise_deprecated(self.env)

    def _l10n_be_codabox_connect(self):
        raise_deprecated(self.env)

    @api.depends("l10n_be_codabox_iap_token")
    def _compute_l10n_be_codabox_is_connected(self):
        self.l10n_be_codabox_is_connected = False

    def l10n_be_codabox_get_number_connections_remaining(self):
        raise_deprecated(self.env)

    def _l10n_be_codabox_revoke(self):
        raise_deprecated(self.env)
