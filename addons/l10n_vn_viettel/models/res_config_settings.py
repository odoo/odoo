# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_vn_type = fields.Char(related='company_id.l10n_vn_type', readonly=False, string="Type")
    l10n_vn_template_code = fields.Char(related='company_id.l10n_vn_template_code', readonly=False, string="Invoice Template")
    l10n_vn_series = fields.Char(related='company_id.l10n_vn_series', readonly=False, string="Series")
    l10n_vn_authority = fields.Char(related='company_id.l10n_vn_authority', readonly=False, string="Authority")
    l10n_vn_base_url = fields.Char(related='company_id.l10n_vn_base_url', readonly=False, string="URL")
    group_l10n_vn_send_validated_invoice = fields.Boolean(string='Send validated Invoices', implied_group='l10n_vn_viettel.group_l10n_vn_send_validated_invoice')
