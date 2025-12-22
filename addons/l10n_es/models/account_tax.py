# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_es_exempt_reason = fields.Selection(
        selection=[
            ('E1', 'Art. 20'),
            ('E2', 'Art. 21'),
            ('E3', 'Art. 22'),
            ('E4', 'Art. 23 y 24'),
            ('E5', 'Art. 25'),
            ('E6', 'Otros'),
        ],
        string="Exempt Reason (Spain)",
    )
    l10n_es_type = fields.Selection(
        selection=[
            ('exento', 'Exento'),
            ('sujeto', 'Sujeto'),
            ('sujeto_agricultura', 'Sujeto Agricultura'),
            ('sujeto_isp', 'Sujeto ISP'),
            ('no_sujeto', 'No Sujeto'),
            ('no_sujeto_loc', 'No Sujeto por reglas de Localization'),
            ('no_deducible', 'No Deducible'),
            ('retencion', 'Retencion'),
            ('recargo', 'Recargo de Equivalencia'),
            ('dua', 'DUA'),
            ('ignore', 'Ignore even the base amount'),
        ],
        string="Tax Type (Spain)", default='sujeto'
    )
    l10n_es_bien_inversion = fields.Boolean('Bien de Inversion', default=False)

    # -------------------------------------------------------------------------
    # EDI HELPERS
    # -------------------------------------------------------------------------

    def _l10n_es_get_regime_code(self):
        # Regime codes (ClaveRegimenEspecialOTrascendencia)
        # NOTE there's 11 more codes to implement, also there can be up to 3 in total
        # See https://www.gipuzkoa.eus/documents/2456431/13761128/Anexo+I.pdf/2ab0116c-25b4-f16a-440e-c299952d683d
        oss_tag = self.env.ref('l10n_eu_oss.tag_oss', raise_if_not_found=False)

        # If there's an OSS tax, it is considered an OSS operation
        if oss_tag and oss_tag in self.invoice_repartition_line_ids.tag_ids:
            return '17'

        if self.filtered(lambda t: t.l10n_es_exempt_reason == 'E2'):
            return '02'

        return '01'

    @api.model
    def _l10n_es_get_sujeto_tax_types(self):
        return ['sujeto', 'sujeto_isp', 'sujeto_agricultura']

    @api.model
    def _l10n_es_get_main_tax_types(self):
        return {'exento', 'sujeto', 'sujeto_agricultura', 'sujeto_isp', 'no_sujeto', 'no_sujeto_loc', 'no_deducible'}
