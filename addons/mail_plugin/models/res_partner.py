# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    iap_enrich_info = fields.Text('IAP Enrich Info', help='IAP response stored as a JSON string',
                                  compute='_compute_partner_iap_info')

    iap_search_domain = fields.Char('Search Domain / Email',
                                compute='_compute_partner_iap_info')

    def _compute_partner_iap_info(self):
        partner_iaps = self.env['res.partner.iap'].sudo().search([('partner_id', 'in', self.ids)])
        partner_iaps_per_partner = {
            partner_iap.partner_id: partner_iap
            for partner_iap in partner_iaps
        }

        for partner in self:
            partner_iap = partner_iaps_per_partner.get(partner)
            if partner_iap:
                partner.iap_enrich_info = partner_iap.iap_enrich_info
                partner.iap_search_domain = partner_iap.iap_search_domain
            else:
                partner.iap_enrich_info = False
                partner.iap_search_domain = False

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        # Not done with inverse method so we do not need to search
        # for existing <res.partner.iap>
        partner_iap_vals_list = [{
            'partner_id': partner.id,
            'iap_enrich_info': vals.get('iap_enrich_info'),
            'iap_search_domain': vals.get('iap_search_domain'),
        } for partner, vals in zip(partners, vals_list) if vals.get('iap_enrich_info') or vals.get('iap_search_domain')]
        self.env['res.partner.iap'].sudo().create(partner_iap_vals_list)
        return partners

    def write(self, vals):
        res = super(ResPartner, self).write(vals)

        if 'iap_enrich_info' in vals or 'iap_search_domain' in vals:
            # Not done with inverse method so we do need to search
            # for existing <res.partner.iap> only once
            partner_iaps = self.env['res.partner.iap'].sudo().search([('partner_id', 'in', self.ids)])
            missing_partners = self
            for partner_iap in partner_iaps:
                if 'iap_enrich_info' in vals:
                    partner_iap.iap_enrich_info = vals['iap_enrich_info']
                if 'iap_search_domain' in vals:
                    partner_iap.iap_search_domain = vals['iap_search_domain']

                missing_partners -= partner_iap.partner_id

            if missing_partners:
                # Create new <res.partner.iap> for missing records
                self.env['res.partner.iap'].sudo().create([
                    {
                        'partner_id': partner.id,
                        'iap_enrich_info': vals.get('iap_enrich_info'),
                        'iap_search_domain': vals.get('iap_search_domain'),
                    } for partner in missing_partners
                ])
        return res
