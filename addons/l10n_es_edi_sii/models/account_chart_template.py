# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template

class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('es_common', 'account.tax')
    def _get_es_edi_sii_account_tax(self):
        return {
            'account_tax_template_s_iva21b': {
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_s_iva21s': {
                'l10n_es_type': 'sujeto',
                'tax_scope': 'service',
            },
            'account_tax_template_s_iva21isp': {
                'l10n_es_type': 'sujeto_isp',
            },
            'account_tax_template_p_iva21_bc': {
                'name': "21% IVA soportado (bienes corrientes)",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_iva21_sc': {
                'name': "21% IVA soportado (servicios corrientes)",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'service',
            },
            'account_tax_template_p_iva21_sp_in': {
                'name': "IVA 21% Adquisición de servicios intracomunitarios",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'service',
            },
            'account_tax_template_p_iva21_ic_bc': {
                'name': "IVA 21% Adquisición Intracomunitaria. Bienes corrientes",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_iva21_ic_bi': {
                'name': "IVA 21% Adquisición Intracomunitaria. Bienes de inversión",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_iva21_ibc': {
                'name': "IVA 21% Importaciones bienes corrientes",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_iva21_ibi': {
                'name': "IVA 21% Importaciones bienes de inversión",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_irpf21td': {
                'name': "Retenciones IRPF (Trabajadores) dinerarios",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_iva4_sp_ex': {
                'name': "IVA 4% Adquisición de servicios extracomunitarios",
                'l10n_es_type': 'sujeto_isp',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_iva10_sp_ex': {
                'name': "IVA 10% Adquisición de servicios extracomunitarios",
                'l10n_es_type': 'sujeto_isp',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_iva21_sp_ex': {
                'name': "IVA 21% Adquisición de servicios extracomunitarios",
                'l10n_es_type': 'sujeto_isp',
                'tax_scope': 'service',
            },
            'account_tax_template_p_iva4_ic_bc': {
                'name': "IVA 4% Adquisición Intracomunitario. Bienes corrientes",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_iva4_ic_bi': {
                'name': "IVA 4% Adquisición Intracomunitario. Bienes de inversión",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_iva10_ic_bc': {
                'name': "IVA 10% Adquisición Intracomunitario. Bienes corrientes",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_iva10_ic_bi': {
                'name': "IVA 10% Adquisición Intracomunitario. Bienes de inversión",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_s_iva0_sp_i': {
                'name': "IVA 0% Prestación de servicios intracomunitario",
                'l10n_es_type': 'no_sujeto',
                'tax_scope': 'service',
            },
            'account_tax_template_s_iva_ns': {
                'name': "No sujeto Repercutido (Servicios)",
                'l10n_es_type': 'no_sujeto',
                'tax_scope': 'service',
            },
            'account_tax_template_s_iva_ns_b': {
                'name': "No sujeto Repercutido (Bienes)",
                'l10n_es_type': 'no_sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_s_iva_e': {
                'name': "IVA 0% Prestación de servicios extracomunitaria",
                'l10n_es_type': 'no_sujeto',
                'tax_scope': 'service',
            },
            'account_tax_template_p_iva4_ibc': {
                'name': "IVA 4% Importaciones bienes corrientes",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_iva4_ibi': {
                'name': "IVA 4% Importaciones bienes de inversión",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_iva10_ibc': {
                'name': "IVA 10% Importaciones bienes corrientes",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_iva10_ibi': {
                'name': "IVA 10% Importaciones bienes de inversión",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_iva4_bi': {
                'name': "4% IVA Soportado (bienes de inversión)",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
                'l10n_es_bien_inversion': True,
            },
            'account_tax_template_p_iva4_sc': {
                'name': "4% IVA soportado (servicios corrientes)",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_iva10_bi': {
                'name': "10% IVA Soportado (bienes de inversión)",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
                'l10n_es_bien_inversion': True,
            },
            'account_tax_template_p_iva21_bi': {
                'name': "21% IVA Soportado (bienes de inversión)",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
                'l10n_es_bien_inversion': True,
            },
            'account_tax_template_p_iva10_bc': {
                'name': "10% IVA soportado (bienes corrientes)",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_iva4_bc': {
                'name': "4% IVA soportado (bienes corrientes)",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_iva10_sc': {
                'name': "10% IVA soportado (servicios corrientes)",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_s_iva0': {
                'name': "IVA Exento Repercutido Sujeto",
                'l10n_es_type': 'exento',
                'l10n_es_exempt_reason': 'E1',
            },
            'account_tax_template_s_iva0_ns': {
                'name': "IVA Exento Repercutido No Sujeto",
                'l10n_es_type': 'ignore',
            },
            'account_tax_template_s_req05': {
                'name': "0.50% Recargo Equivalencia Ventas",
                'l10n_es_type': 'recargo',
            },
            'account_tax_template_s_iva4b': {
                'name': "IVA 4% (Bienes)",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_s_iva10b': {
                'name': "IVA 10% (Bienes)",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_iva0_nd': {
                'name': "21% IVA Soportado no deducible",
                'l10n_es_type': 'no_deducible',
            },
            'account_tax_template_p_iva10_nd': {
                'name': "10% IVA Soportado no deducible",
                'l10n_es_type': 'no_deducible',
            },
            'account_tax_template_p_iva4_nd': {
                'name': "4% IVA Soportado no deducible",
                'l10n_es_type': 'no_deducible',
            },
            'account_tax_template_s_iva4s': {
                'name': "IVA 4% (Servicios)",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'service',
            },
            'account_tax_template_s_iva10s': {
                'name': "IVA 10% (Servicios)",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'service',
            },
            'account_tax_template_s_req014': {
                'name': "1.4% Recargo Equivalencia Ventas",
                'l10n_es_type': 'recargo',
            },
            'account_tax_template_s_req52': {
                'name': "5.2% Recargo Equivalencia Ventas",
                'l10n_es_type': 'recargo',
            },
            'account_tax_template_p_iva0_bc': {
                'name': "IVA Soportado exento (operaciones corrientes)",
                'l10n_es_type': 'sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_iva0_ns': {
                'name': "IVA Soportado no sujeto (Servicios)",
                'l10n_es_type': 'no_sujeto',
                'tax_scope': 'service',
            },
            'account_tax_template_p_iva0_ns_b': {
                'name': "IVA Soportado no sujeto (Bienes)",
                'l10n_es_type': 'no_sujeto',
                'tax_scope': 'consu',
            },
            'account_tax_template_s_irpf9': {
                'name': "Retenciones a cuenta IRPF 9%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_s_irpf18': {
                'name': "Retenciones a cuenta IRPF 18%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_s_irpf19': {
                'name': "Retenciones a cuenta IRPF 19%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_s_irpf19a': {
                'name': "Retenciones a cuenta 19% (Arrendamientos)",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_s_irpf195a': {
                'name': "Retenciones a cuenta 19,5% (Arrendamientos)",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_irpf19': {
                'name': "Retenciones IRPF 19%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_irpf20a': {
                'name': "Retenciones 20% (Arrendamientos)",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_irpf18': {
                'name': "Retenciones IRPF 18%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_irpf19a': {
                'name': "Retenciones 19% (Arrendamientos)",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_irpf195a': {
                'name': "Retenciones 19,5% (Arrendamientos)",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_irpf7': {
                'name': "Retenciones IRPF 7%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_irpf9': {
                'name': "Retenciones IRPF 9%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_irpf24': {
                'name': "Retenciones IRPF 14%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_s_irpf20': {
                'name': "Retenciones a cuenta IRPF 20%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_s_irpf20a': {
                'name': "Retenciones a cuenta 20% (Arrendamientos)",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_s_irpf24': {
                'name': "Retenciones a cuenta IRPF 24%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_iva12_agr': {
                'name': "12% IVA Soportado régimen agricultura",
                'l10n_es_type': 'sujeto_agricultura',
            },
            'account_tax_template_p_iva105_gan': {
                'name': "10,5% IVA Soportado régimen ganadero o pesca",
            },
            'account_tax_template_s_iva0_e': {
                'name': "IVA 0% Exportaciones",
                'l10n_es_type': 'exento',
                # E2 for exportation
                'l10n_es_exempt_reason': 'E2',
                'tax_scope': 'consu',
            },
            'account_tax_template_s_iva0_ic': {
                'name': "IVA 0% Entregas Intracomunitarias exentas",
                'l10n_es_type': 'exento',
                # E5  for intra-community
                'l10n_es_exempt_reason': 'E5',
                'tax_scope': 'consu',
            },
            'account_tax_template_p_req014': {
                'name': "1.4% Recargo Equivalencia Compras",
                'l10n_es_type': 'recargo',
            },
            'account_tax_template_p_req05': {
                'name': "0.50% Recargo Equivalencia Compras",
                'l10n_es_type': 'recargo',
            },
            'account_tax_template_p_req52': {
                'name': "5.2% Recargo Equivalencia Compras",
                'l10n_es_type': 'recargo',
            },
            'account_tax_template_s_irpf1': {
                'name': "Retenciones a cuenta IRPF 1%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_s_irpf2': {
                'name': "Retenciones a cuenta IRPF 2%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_s_irpf21': {
                'name': "Retenciones a cuenta IRPF 21%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_s_irpf21a': {
                'name': "Retenciones a cuenta 21% (Arrendamientos)",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_s_irpf7': {
                'name': "Retenciones a cuenta IRPF 7%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_s_irpf15': {
                'name': "Retenciones a cuenta IRPF 15%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_irpf1': {
                'name': "Retenciones IRPF 1%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_irpf15': {
                'name': "Retenciones IRPF 15%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_irpf21t': {
                'name': "Retenciones IRPF (Trabajadores)",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_iva10_sp_in': {
                'name': "IVA 10% Adquisición de servicios intracomunitarios",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_iva4_sp_in': {
                'name': "IVA 4% Adquisición de servicios intracomunitarios",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_irpf21te': {
                'name': "Retenciones IRPF (Trabajadores) en especie",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_irpf20': {
                'name': "Retenciones IRPF 20%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_irpf21a': {
                'name': "Retenciones 21% (Arrendamientos)",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_irpf21p': {
                'name': "Retenciones IRPF 21%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_irpf2': {
                'name': "Retenciones IRPF 2%",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_s_iva0_isp': {
                'name': "IVA 0% Venta con Inversión del Sujeto Pasivo",
                'l10n_es_type': 'sujeto_isp',
            },
            'account_tax_template_p_iva4_isp': {
                'name': "IVA 4% Compra con Inversión del Sujeto Pasivo Nacional",
                'l10n_es_type': 'sujeto_isp',
            },
            'account_tax_template_p_iva10_isp': {
                'name': "IVA 10% Compra con Inversión del Sujeto Pasivo Nacional",
                'l10n_es_type': 'sujeto_isp',
            },
            'account_tax_template_p_iva21_isp': {
                'name': "IVA 21% Compra con Inversión del Sujeto Pasivo Nacional",
                'l10n_es_type': 'sujeto_isp',
            },
            'account_tax_template_p_rp19': {
                'name': "Retenciones 19% (préstamos)",
                'l10n_es_type': 'retencion',
            },
            'account_tax_template_p_rrD19': {
                'name': "Retenciones 19% (reparto de dividendos)",
                'l10n_es_type': 'retencion',
            },
        }
