# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.multi
    def _get_fp_vals(self, company, position):
        res = super()._get_fp_vals(company, position)
        if company.country_id == self.env.ref('base.ar'):
            res['l10n_ar_afip_responsability_type_codes'] = \
                position.l10n_ar_afip_responsability_type_codes
        return res

    @api.multi
    def _prepare_all_journals(self, acc_template_ref, company,
                              journals_dict=None):
        """ If argentinian chart, we don't create sales journal as we need more
        data to create it properly
        """
        res = super(
            AccountChartTemplate, self)._prepare_all_journals(
            acc_template_ref, company, journals_dict=journals_dict)

        if company.country_id == self.env.ref('base.ar'):
            for vals in res:
                if vals['type'] == 'sale':
                    vals.update({
                        'l10n_ar_afip_pos_number': 1,
                        'l10n_ar_afip_pos_partner_id': company.partner_id.id,
                        'l10n_ar_afip_pos_system': 'II_IM',
                        'l10n_ar_share_sequences': True,
                    })
        return res
