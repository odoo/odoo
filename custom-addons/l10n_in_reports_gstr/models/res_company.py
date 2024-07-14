# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_in_gstr_gst_username = fields.Char(string="GST User Name (IN)", groups="base.group_system")
    l10n_in_gstr_gst_token = fields.Char(string="GST Token (IN)", groups="base.group_system")
    l10n_in_gstr_gst_token_validity = fields.Datetime(string="GST Token (IN) Valid Until", groups="base.group_system")
    l10n_in_gstr_gst_auto_refresh_token = fields.Boolean(
        string="GST (IN) Token Auto Refresh", groups="base.group_system")
    l10n_in_gstr_gst_production_env = fields.Boolean(
        string="GST (IN) Is production environment",
        help="Enable the use of production credentials",
        groups="base.group_system",
    )

    def _is_l10n_in_gstr_token_valid(self):
        self.ensure_one()
        return (
            self.sudo().l10n_in_gstr_gst_token_validity
            and self.sudo().l10n_in_gstr_gst_token_validity > fields.Datetime.now()
        )
