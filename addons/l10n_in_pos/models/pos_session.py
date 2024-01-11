# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_data_params(self, config_id):
        params = super()._load_data_params(config_id)
        params['product.product']['fields'] += ['l10n_in_hsn_code']
        params['account.account.tag'] = self._get_account_account_tag_params()
        params['account.tax.repartition.line']['fields'] += ['tag_ids']
        return params

    def load_data(self, models_to_load, only_data=False):
        response = super().load_data(models_to_load, only_data)
        response['custom']['account_tag_by_xml_ref_id'] = self._get_account_tag_by_xml_ref_id()
        return response

    def _get_account_account_tag_params(self):
        return {
            'domain': self._get_account_account_tag_domain(),
            'fields': ['id', 'name', 'applicability'],
        }

    def _get_account_account_tag_domain(self):
        return [
            ('applicability', '=', 'taxes'),
        ]

    def _get_account_tag_by_xml_ref_id(self):
        tag_ids = self.env['account.account.tag'].search(self._get_account_account_tag_domain())
        tag_with_xml_ids = self.env['ir.model.data'].sudo().search(
            [
                ('res_id', 'in', tag_ids.ids), ('model', '=', 'account.account.tag')
            ]
        )
        gst_tags = {tag_ref.res_id: "%s.%s" % (tag_ref.module, tag_ref.name) for tag_ref in tag_with_xml_ids}
        return gst_tags

    @api.model
    def _load_onboarding_main_config_data(self, shop_config):
        if shop_config.company_id.country_code == 'IN' and not shop_config.company_id.state_id:
            return

        super()._load_onboarding_main_config_data(shop_config)
