# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.osv import expression


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_l10n_in_reseller = fields.Boolean(implied_group='l10n_in.group_l10n_in_reseller', string="Manage Reseller(E-Commerce)")
    module_l10n_in_edi = fields.Boolean('Indian Electronic Invoicing')
    module_l10n_in_edi_ewaybill = fields.Boolean('Indian Electronic Waybill')
    l10n_in_gsp = fields.Selection(selection=[
        ('bvm', 'BVM IT Consulting'),
        ('tera', 'Tera Software (Deprecated)'),
    ], string="GSP",
        inverse="_set_l10n_in_gsp",  # use an inverse method to invalidate existing tokens if the GSP is changed
        store=False,
        help="Select the GST Suvidha Provider (GSP) you want to use for GST services.",
    )

    def _l10n_in_is_first_time_setup(self):
        """
            Check if at least one company for India has been configured with the localization settings.
            If not, it means it's the first time setup.
        """
        all_validity_fields = ['l10n_in_gstr_gst_token_validity', 'l10n_in_edi_token_validity', 'l10n_in_edi_ewaybill_auth_validity']
        validity_fields = (field_name for field_name in self.company_id._fields if field_name in all_validity_fields)
        if validity_fields:
            validity_fields_domain = expression.OR([[(field_name, '!=', False)] for field_name in validity_fields])
            configured_company_count = self.env['res.company'].sudo().search_count([
                ('account_fiscal_country_id.code', '=', 'IN'),
                *validity_fields_domain
            ])
            return not configured_company_count
        return True

    def get_values(self):
        res = super().get_values()
        res['l10n_in_gsp'] = self.env['ir.config_parameter'].sudo().get_param('l10n_in.gsp_provider')
        if not res['l10n_in_gsp']:
            if self._l10n_in_is_first_time_setup():
                # Default to BVM for new databases setting up India localization for the first time
                res['l10n_in_gsp'] = 'bvm'
            else:
                res['l10n_in_gsp'] = 'tera'
        return res

    def _l10n_in_gsp_provider_changed(self):
        """ Hook to be overridden in other modules to handle GSP provider change. """
        self.ensure_one()
        self.env['ir.config_parameter'].sudo().set_param('l10n_in.gsp_provider', self.l10n_in_gsp)

    def _set_l10n_in_gsp(self):
        gsp_before = self.env['ir.config_parameter'].sudo().get_param('l10n_in.gsp_provider')
        for config in self:
            if gsp_before != config.l10n_in_gsp:
                config._l10n_in_gsp_provider_changed()
            return
