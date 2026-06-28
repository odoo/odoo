# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_eg_client_identifier = fields.Char('ETA Client ID', groups="base.group_erp_manager")
    l10n_eg_client_secret = fields.Char('ETA Secret', groups="base.group_erp_manager")
    l10n_eg_production_env = fields.Boolean('In Production Environment')
    l10n_eg_invoicing_threshold = fields.Float('Invoicing Threshold', default=0.0,
                                               help="Threshold at which you are required to give the VAT number "
                                                    "of the customer. ")
    l10n_eg_building_no = fields.Char("Building No.", compute='_compute_address', inverse='_inverse_l10n_eg_building_no')

    def _get_company_address_field_names(self):
        """Override to add EG specific address fields"""
        return super()._get_company_address_field_names() + ["l10n_eg_building_no"]

    def _inverse_l10n_eg_building_no(self):
        for company in self:
            company.partner_id.l10n_eg_building_no = company.l10n_eg_building_no
