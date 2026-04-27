# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _configure_payroll_account_ch(self, companies):
        account_codes = [
            '1090',  # Salary Pass Through Account
            '1091',  # Transfer account: Salaries
            '2270',  # Health insurance AHV, IV, EO, ALV
            '2210',  # Short Term liabilities
            '2271',  # LPP Provision
            '2272',  # Health insurance CAF
            '2273',  # Assurance Accident
            '2274',  # Daily Sickness Insurance
            '2279',  # Source Tax
            '2350',  # 13th month provision
            '2351',  # 14th month provision
            '5000',  # Wages
            '5001',  # Social insurance Payments
            '5002',  # Profit Sharing
            '5005',  # 13th Month
            '5011',  # 14th Month
            '5007',  # Bonus
            '5010',  # Commissions
            '5700',  # AHV
            '5710',  # FAK
            '5710',  # FAK
            '5720',  # LPP
            '5730',  # AANP
            '5731',  # LAAC
            '5740',  # IJM
            '5790',  # IS
            '5800',  # Other Expenses
            '5810',  # Professional Training
            '5820',  # Travel Expenses
            '5830',  # Representation fees Expenses
            '5832',  # Fixed Rate Expenses
            '5890',  # Rate of personal Use
            '5891',  # Compensation Company Car
            '6200',  # Vehicle Expenses
        ]

        rules_mapping = defaultdict(dict)

        # ================================================ #
        #           CH Employee Payroll Structure          #
        # ================================================ #

        rules_with_default_mapping = [
            "1000", "1001", "1005", "1006", "1065", "1061", "1067", "1160", "1161", "1015", "1016", "1017",
            "1018", "1020", "1021", "1031", "1032", "1033", "1034", "1040", "1050", "1055", "1056", "1060",
            "1070", "1071", "1072", "1074", "1076", "1100", "1101", "1102", "1103", "1104", "1110", "1111",
            "1131", "1162", "1163", "1230", "1231", "1299", "1300", "1301", "1302", "1303", "1304", "1305",
            "1306", "1307", "1500", "1501", "1503", "1953", "1955", "1973", "2025", "2026", "2027", "2030",
            "2031", "2032", "2035", "2040", "2070", "4900", "1207", "1208"
        ]

        bonuses = [
            "1010", "1030", "1073", "1075", "1112", "1130", "1202", "1204", "1209", "1210", "1212", "1213",
            "1214", "1215", "1216", "1217", "1219", "1232", "1250", "3032"
        ]

        bonus_rules = self.env['hr.salary.rule'].search([('l10n_ch_code', 'in', bonuses), ('struct_id', '=', self.env.ref('l10n_ch_hr_payroll_elm_transmission.hr_payroll_structure_ch_elm').id)])

        for rule in bonus_rules:
            rules_mapping[rule]['debit'] = '5007'
            rules_mapping[rule]['credit'] = '1090'

        wage_rules = self.env['hr.salary.rule'].search([('l10n_ch_code', 'in', rules_with_default_mapping), ('struct_id', '=', self.env.ref('l10n_ch_hr_payroll_elm_transmission.hr_payroll_structure_ch_elm').id)])

        for rule in wage_rules:
            rules_mapping[rule]['debit'] = '5000'
            rules_mapping[rule]['credit'] = '1090'


        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1510')
        rules_mapping[rule]['debit'] = '5002'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1218')
        rules_mapping[rule]['debit'] = '5002'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1211')
        rules_mapping[rule]['debit'] = '5010'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1400')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1401')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1410')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1411')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1420')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1900')
        rules_mapping[rule]['debit'] = '5890'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1901')
        rules_mapping[rule]['debit'] = '5890'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1902')
        rules_mapping[rule]['debit'] = '5890'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1910')
        rules_mapping[rule]['debit'] = '1090'
        rules_mapping[rule]['credit'] = '6200'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1950')
        rules_mapping[rule]['debit'] = '5890'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1960')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1960')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1961')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1962')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1971')
        rules_mapping[rule]['debit'] = '5740'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1972')
        rules_mapping[rule]['debit'] = '5720'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1974')
        rules_mapping[rule]['debit'] = '5740'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1975')
        rules_mapping[rule]['debit'] = '5730'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1976')
        rules_mapping[rule]['debit'] = '5731'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1977')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1977')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1978')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1979')
        rules_mapping[rule]['debit'] = '5790'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_1980')
        rules_mapping[rule]['debit'] = '5810'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_1200')
        rules_mapping[rule]['debit'] = '2350'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_1205')
        rules_mapping[rule]['debit'] = '2351'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_13_prov')
        rules_mapping[rule]['debit'] = '5005'
        rules_mapping[rule]['credit'] = '2350'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_14_prov')
        rules_mapping[rule]['debit'] = '5011'
        rules_mapping[rule]['credit'] = '2351'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_2000')
        rules_mapping[rule]['debit'] = '5001'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_2005')
        rules_mapping[rule]['debit'] = '5001'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_2010')
        rules_mapping[rule]['debit'] = '5001'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_2015')
        rules_mapping[rule]['debit'] = '5001'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_2020')
        rules_mapping[rule]['debit'] = '5001'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_2021')
        rules_mapping[rule]['debit'] = '5001'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_2022')
        rules_mapping[rule]['debit'] = '5001'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_2050')
        rules_mapping[rule]['credit'] = '1090'
        rules_mapping[rule]['debit'] = '5000'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_2060')
        rules_mapping[rule]['debit'] = '5000'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_2065')
        rules_mapping[rule]['debit'] = '1090'
        rules_mapping[rule]['credit'] = '5000'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_2075')
        rules_mapping[rule]['debit'] = '5000'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3000')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3001')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3004_fcf')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3005_fcf')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3010')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3011')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3014_fcf')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3015_fcf')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3030')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3031')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3032')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3032')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3033')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3038')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3035')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3036')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3037')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_5010')
        rules_mapping[rule]['debit'] = '2270'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_5020')
        rules_mapping[rule]['debit'] = '2270'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_5400')
        rules_mapping[rule]['debit'] = '2270'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_compl_ac')
        rules_mapping[rule]['debit'] = '2270'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_7400')
        rules_mapping[rule]['debit'] = '5700'
        rules_mapping[rule]['credit'] = '2270'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_7010')
        rules_mapping[rule]['debit'] = '5700'
        rules_mapping[rule]['credit'] = '2270'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_7011')
        rules_mapping[rule]['debit'] = '5700'
        rules_mapping[rule]['credit'] = '2270'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_5020_comp')
        rules_mapping[rule]['debit'] = '5700'
        rules_mapping[rule]['credit'] = '2270'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_compl_ac_comp')
        rules_mapping[rule]['debit'] = '5700'
        rules_mapping[rule]['credit'] = '2270'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_aap_comp')
        rules_mapping[rule]['debit'] = '5730'
        rules_mapping[rule]['credit'] = '2273'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_5040_comp')
        rules_mapping[rule]['debit'] = '5730'
        rules_mapping[rule]['credit'] = '2273'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_laac_comp_1')
        rules_mapping[rule]['debit'] = '5730'
        rules_mapping[rule]['credit'] = '2273'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_laac_comp_2')
        rules_mapping[rule]['debit'] = '5730'
        rules_mapping[rule]['credit'] = '2273'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_5040')
        rules_mapping[rule]['debit'] = '2273'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_laac1')
        rules_mapping[rule]['debit'] = '2273'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_laac_2')
        rules_mapping[rule]['debit'] = '2273'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_ijm_1')
        rules_mapping[rule]['debit'] = '2274'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_ijm_2')
        rules_mapping[rule]['debit'] = '2274'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_ijm_comp_1')
        rules_mapping[rule]['debit'] = '5740'
        rules_mapping[rule]['credit'] = '2274'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_ijm_comp_2')
        rules_mapping[rule]['debit'] = '5740'
        rules_mapping[rule]['credit'] = '2274'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_5050')
        rules_mapping[rule]['debit'] = '2271'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_5052')
        rules_mapping[rule]['debit'] = '2271'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_7050')
        rules_mapping[rule]['debit'] = '5720'
        rules_mapping[rule]['credit'] = '2271'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_7052')
        rules_mapping[rule]['debit'] = '5720'
        rules_mapping[rule]['credit'] = '2271'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_5111')
        rules_mapping[rule]['debit'] = '5720'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_5112')
        rules_mapping[rule]['debit'] = '5720'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_5051')
        rules_mapping[rule]['debit'] = '2271'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_7051')
        rules_mapping[rule]['debit'] = '5720'
        rules_mapping[rule]['credit'] = '2271'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_5061')
        rules_mapping[rule]['debit'] = '2279'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_5061_nk')
        rules_mapping[rule]['debit'] = '2279'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_5060')
        rules_mapping[rule]['debit'] = '2279'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_5060_manual')
        rules_mapping[rule]['debit'] = '2279'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_5070')
        rules_mapping[rule]['debit'] = '2272'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_7070')
        rules_mapping[rule]['debit'] = '2272'
        rules_mapping[rule]['credit'] = '5710'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_5080')
        rules_mapping[rule]['debit'] = '1090'
        rules_mapping[rule]['credit'] = '5891'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_5081')
        rules_mapping[rule]['debit'] = '1090'
        rules_mapping[rule]['credit'] = '2210'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_5082')
        rules_mapping[rule]['debit'] = '1090'
        rules_mapping[rule]['credit'] = '2210'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_5100')
        rules_mapping[rule]['debit'] = '5800'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_5110')
        rules_mapping[rule]['debit'] = '5000'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_5310')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_7310')
        rules_mapping[rule]['debit'] = '1090'
        rules_mapping[rule]['credit'] = '1091'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_5300')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_7300')
        rules_mapping[rule]['debit'] = '1090'
        rules_mapping[rule]['credit'] = '1091'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_6000')
        rules_mapping[rule]['debit'] = '5832'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_6020')
        rules_mapping[rule]['debit'] = '5832'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_6030')
        rules_mapping[rule]['debit'] = '5800'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_6035')
        rules_mapping[rule]['debit'] = '1091'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_6040')
        rules_mapping[rule]['debit'] = '5830'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_6050')
        rules_mapping[rule]['debit'] = '5832'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_6070')
        rules_mapping[rule]['debit'] = '5832'
        rules_mapping[rule]['credit'] = '1090'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_6510')
        rules_mapping[rule]['debit'] = '1090'
        rules_mapping[rule]['credit'] = '1091'

        rule = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_rule_6600')
        rules_mapping[rule]['debit'] = '1090'
        rules_mapping[rule]['credit'] = '1091'



        self._configure_payroll_account(
            companies,
            "CH",
            account_codes=account_codes,
            rules_mapping=rules_mapping,
        )
