from odoo import models
from odoo.addons.account.models.chart_template import template

FR_DOMESTIC = 'fiscal_position_template_domestic'
RE_DOMESTIC = 'fiscal_position_template_domestic_re'
FR_MC_B2B = 'fiscal_position_template_re_fr_b2b'
FR_MC_B2C = 'fiscal_position_template_re_fr_b2c'
GP_MQ = 'fiscal_position_template_re_gp_mq'
GF_YT = 'fiscal_position_template_re_gf_yt'
EU_B2B = 'fiscal_position_template_intraeub2b'
EU_B2C = 'fiscal_position_template_intraeub2c'
OUTSIDE_EU = 'fiscal_position_template_import_export'
OUTSIDE_RE = (FR_MC_B2B, FR_MC_B2C, GP_MQ, GF_YT, EU_B2B, EU_B2C, OUTSIDE_EU)

# 8.5% S / 2.1% S are kept unchanged for these positions
RE_SERVICES_KEPT = (RE_DOMESTIC, FR_MC_B2C, GP_MQ, EU_B2C)

# xmlid: (fiscal positions, taxes replaced by this one)
# A `None` value for the replaced taxes keeps what the French template defines.
RE_TAX_FISCAL_POSITIONS = {
    'tva_specifique_encaissement': (RE_SERVICES_KEPT, None),
    'tva_super_reduite_encaissement': (RE_SERVICES_KEPT, None),
    'tva_acq_encaissement_specifique': (RE_SERVICES_KEPT, None),
    'tva_acq_encaissement_super_reduite': (RE_SERVICES_KEPT, None),
    # France - Monaco B2B: 8.5% S -> 20% S. Not linked to the domestic
    # position, otherwise 8.5% S would also be replaced in La Réunion.
    'tva_normale_encaissement': ((FR_MC_B2B,), 'tva_specifique_encaissement'),
    'tva_acq_encaissement': ((FR_MC_B2B,), 'tva_acq_encaissement_specifique'),
    # Goods sold outside La Réunion: 0% export (La Réunion is outside the EU VAT territory)
    'tva_sale_good_export_0': (OUTSIDE_RE, None),
    'tva_sale_good_intra_0': ((EU_B2B,), ''),
    # Goods bought outside La Réunion: 0% import
    'tva_purchase_goods_0': (
        OUTSIDE_RE,
        'tva_acq_normale,tva_acq_specifique,tva_acq_intermediaire,tva_acq_reduite,tva_acq_super_reduite',
    ),
    # Guyane - Mayotte: VAT not applicable (art. 294-1 CGI)
    'tva_sale_service_export_0': ((GF_YT, OUTSIDE_EU), None),
}


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('re', 'account.fiscal.position')
    def _get_re_account_fiscal_position(self):
        return self._parse_csv('re', 'account.fiscal.position', module='l10n_re')

    @template('re', 'account.tax')
    def _get_re_account_tax(self):
        """ Remap the French taxes on the La Réunion fiscal positions.

        Taxes not listed in RE_TAX_FISCAL_POSITIONS keep the French configuration, except:
        - the French domestic taxes are moved to the La Réunion domestic position;
        - the French import and intra-EU taxes on goods purchases no longer replace
          anything, so goods bought outside La Réunion only get 0% import.
        """
        tax_data = {}
        for xmlid, values in self._parse_csv('re', 'account.tax').items():
            fiscal_positions = (values.get('fiscal_position_ids') or '').split(',')
            if xmlid in RE_TAX_FISCAL_POSITIONS:
                re_fiscal_positions, original_taxes = RE_TAX_FISCAL_POSITIONS[xmlid]
                tax_data[xmlid] = {'fiscal_position_ids': ','.join(re_fiscal_positions)}
                if original_taxes is not None:
                    tax_data[xmlid]['original_tax_ids'] = original_taxes
            elif FR_DOMESTIC in fiscal_positions:
                tax_data[xmlid] = {'fiscal_position_ids': RE_DOMESTIC}
            elif (
                values.get('type_tax_use') == 'purchase'
                and values.get('tax_scope') == 'consu'
                and values.get('original_tax_ids')
            ):
                tax_data[xmlid] = {'original_tax_ids': ''}
        return tax_data
