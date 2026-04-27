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
    l10n_in_gstr_activate_einvoice_fetch = fields.Selection(
        string='Fetch Vendor E-Invoiced Documents',
        selection=[
            ('do_nothing', 'Do Nothing'),
            ('manual', 'Fetch Manually'),
            ('automatic', 'Fetch Automatically'),
        ], default="do_nothing",
        help="""
            Do Nothing - Not Activated
            Fetch Manually - Invoices are created without lines but an IRN number, but there is a button to get the lines.
            Fetch Automatically - Existing documents with an IRN are automatically updated, and incoming documents are fetched and populated automatically."""
    )

    def _is_l10n_in_gstr_token_valid(self):
        self.ensure_one()
        return (
            self.sudo().l10n_in_gstr_gst_token_validity
            and self.sudo().l10n_in_gstr_gst_token_validity > fields.Datetime.now()
        )
