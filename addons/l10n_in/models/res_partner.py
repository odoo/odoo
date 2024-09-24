# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

TEST_GST_NUMBER = "36AABCT1332L011"

class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_in_gst_treatment = fields.Selection([
            ('regular', 'Registered Business - Regular'),
            ('composition', 'Registered Business - Composition'),
            ('unregistered', 'Unregistered Business'),
            ('consumer', 'Consumer'),
            ('overseas', 'Overseas'),
            ('special_economic_zone', 'Special Economic Zone'),
            ('deemed_export', 'Deemed Export'),
            ('uin_holders', 'UIN Holders'),
        ], string="GST Treatment")

    l10n_in_pan = fields.Char(
        string="PAN",
        help="PAN enables the department to link all transactions of the person with the department.\n"
             "These transactions include taxpayments, TDS/TCS credits, returns of income/wealth/gift/FBT,"
             " specified transactions, correspondence, and so on.\n"
             "Thus, PAN acts as an identifier for the person with the tax department."
    )

    display_pan_warning = fields.Boolean(string="Display pan warning", compute="_compute_display_pan_warning")

    @api.depends('l10n_in_pan')
    def _compute_display_pan_warning(self):
        for partner in self:
            partner.display_pan_warning = partner.vat and partner.l10n_in_pan and partner.l10n_in_pan != partner.vat[2:12]

    @api.onchange('company_type')
    def onchange_company_type(self):
        res = super().onchange_company_type()
        if self.country_id and self.country_id.code == 'IN':
            self.l10n_in_gst_treatment = (self.company_type == 'company') and 'regular' or 'consumer'
        return res

    @api.onchange('country_id')
    def _onchange_country_id(self):
        res = super()._onchange_country_id()
        if self.country_id and self.country_id.code != 'IN':
            self.l10n_in_gst_treatment = 'overseas'
        elif self.country_id and self.country_id.code == 'IN':
            self.l10n_in_gst_treatment = (self.company_type == 'company') and 'regular' or 'consumer'
        return res

    @api.onchange('vat')
    def onchange_vat(self):
        if self.vat and self.check_vat_in(self.vat):
            state_id = self.env['res.country.state'].search([('l10n_in_tin', '=', self.vat[:2])], limit=1)
            if state_id:
                self.state_id = state_id
            if self.vat[2].isalpha():
                self.l10n_in_pan = self.vat[2:12]

    @api.model
    def _commercial_fields(self):
        res = super()._commercial_fields()
        return res + ['l10n_in_gst_treatment', 'l10n_in_pan']

    def check_vat_in(self, vat):
        """
            This TEST_GST_NUMBER is used as test credentials for EDI
            but this is not a valid number as per the regular expression
            so TEST_GST_NUMBER is considered always valid
        """
        if vat == TEST_GST_NUMBER:
            return True
        return super().check_vat_in(vat)

    @api.model
    def _l10n_in_get_partner_vals_by_vat(self, vat):
        partner_details = self.read_by_vat(vat)
        partner_data = partner_details[0] if partner_details else {}
        if partner_data:
            partner_gid = partner_data.get('partner_gid')
            if partner_gid:
                partner_data = self.enrich_company(company_domain=None, partner_gid=partner_gid, vat=partner_data.get('vat'))
                partner_data = self._iap_replace_logo(partner_data)
            return {
                'name': partner_data.get('name'),
                'company_type': 'company',
                'partner_gid': partner_gid,
                'vat': partner_data.get('vat'),
                'l10n_in_gst_treatment': 'regular',
                'image_1920': partner_data.get('image_1920'),
                'street': partner_data.get('street'),
                'street2': partner_data.get('street2'),
                'city': partner_data.get('city'),
                'state_id': partner_data.get('state_id', {}).get('id', False),
                'country_id': partner_data.get('country_id', {}).get('id', False),
                'zip': partner_data.get('zip'),
            }
        return {}
