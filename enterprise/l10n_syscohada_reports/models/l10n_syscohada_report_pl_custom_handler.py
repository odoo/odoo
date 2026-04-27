from odoo import models


class L10nSyscohadaReportPlCustomHandler(models.AbstractModel):
    _name = 'l10n_syscohada.report.pl.custom.handler'
    _inherit = 'account.report.custom.handler'
    _description = "SYSCOHADA Profit & Loss Custom Handler"

    def _report_custom_engine_get_note(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return {
            'Ventes_de_marchandises': '21',
            'Achats_de_marchandises': '22',
            'Variation_de_stocks_mar': '6',
            'Ventes_prod_fab': '21',
            'Travaux_services_vn': '21',
            'Produits_accessoires': '21',
            'Produc_stck': '6',
            'Produc_immo': '21',
            'Sub_exp': '21',
            'Autres_prod': '21',
            'Transf_chrg_exp': '12',
            'Achats_mat_prem': '22',
            'Var_stocks_mp': '6',
            'Autres_achats': '22',
            'Var_stocks_autres_app': '6',
            'Transports': '23',
            'Services_ext': '24',
            'impots_et_taxes': '25',
            'Autres_charges': '26',
            'Charges_pers': '27',
            'Reprise_amr_prov_dep': '28',
            'Dot_am_prov_dep': '3C-28',
            'Revenu_fin_ass': '29',
            'Reprise_prov_dep_fin': '28',
            'Transferts_charges_fin': '12',
            'Frais_fin_chrg_ass': '29',
            'Dot_prov_dep_fin': '3C-28',
            'Prod_cess_immo': '3D',
            'Autres_prod_HAO': '30',
            'Val_comp_cess_immo': '3D',
            'Autres_chrg_HAO': '30',
            'Part_trav': '30',
        }

    def _custom_line_postprocessor(self, report, options, lines):
        lines = super()._custom_line_postprocessor(report, options, lines)

        for line in lines:
            columns = line['columns']
            note_column = next((column for column in columns if column.get('expression_label') == 'note'), None)
            balance_column = next((column for column in columns if column.get('expression_label') == 'balance'), None)
            if note_column and balance_column and balance_column['is_zero']:
                note_column.update({
                    'name': '',
                    'no_format': '',
                    'is_zero': True,
                })

        return lines
