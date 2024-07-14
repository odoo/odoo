# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_l10n_ch_hr_payroll_account.tests.common import TestL10NChHrPayrollAccountCommon
from odoo.tests.common import tagged


@tagged('post_install_l10n', 'post_install', '-at_install', 'swissdec')
class TestSwissdecRuleDefinitions(TestL10NChHrPayrollAccountCommon):
    """
    Testing Objectives:
    - Check that all basic rules are correctly defined
    """

    def test_swissdec_rules_definitions(self):
        rules_data = [
            (1000, "Salaire mensuel", 5000, "+", 1, 1, 1, 1, 1, 1, 13, 0, 1, 1, 0, "I", ""),
            (1001, "Correction des salaires", 5000, "+", 1, 1, 1, 1, 1, 1, "", 0, 1, 1, 0, "I", ""),
            (1005, "Salaire horaire", 5000, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 1, 0, "I", ""),
            (1006, "Salaire à la leçon", 5000, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 1, 0, "I", ""),
            (1010, "Honoraires", 5000, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 1, 0, "I", ""),
            (1031, "Indemnité de fonction", 5001, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 1, 0, "I", ""),
            (1033, "Indemnité de résidence", 5001, "+", 1, 1, 1, 1, 1, 1, 12, 0, 1, 1, 0, "I", ""),
            (1061, "Heures supplémentaires 125%", 5002, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 1, 0, "", "P"),
            (1065, "Heures supplémentaires", 5002, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 1, 0, "", "P"),
            (1067, "Heures supplémentaires après le départ", 5002, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 3, 0, "", "P"),
            (1070, "Indemnité travail par équipes", 5001, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 1, 0, "J", ""),
            (1071, "Indemnité pour service de piquet", 5001, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 1, 0, "J", ""),
            (1073, "Indemnité de dimanche", 5001, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 1, 0, "J", ""),
            (1076, "Allocations de nuit", 5001, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 1, 0, "J", ""),
            (1160, "Indemnité de vacances", 5004, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 1, 0, "I", ""),
            (1161, "Indemnité pour jour férié", 5004, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 1, 0, "I", ""),
            (1162, "Paiement des vacances", 5004, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 1, 0, "", "P"),
            (1163, "Paiement des vacances après le départ", 5004, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 3, 0, "", "P"),
            (1200, "13ème salaire", 5005, "+", 1, 1, 1, 1, 1, 0, "", 0, 1, 1, 0, "", "O"),
            (1201, "Gratification", 5006, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 3, 0, "", "Q"),
            (1205, "14ème salaire", 5005, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 1, 0, "", "O"),
            (1209, "Paiement de la prime l'année précédente", 5007, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 3, 0, "", "Q"),
            (1210, "Bonus", 5007, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 3, 0, "", "Q"),
            (1212, "Indemnité spéciale", 5007, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 3, 0, "", "Q"),
            (1216, "Prime pour proposition d'amélioration", 5003, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 3, 0, "", "Q"),
            (1218, "Commission", 5007, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 1, 0, "I", ""),
            (1230, "Cadeau pour ancienneté de service", 5009, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 3, 0, "", "Q"),
            (1401, "Indemnité de départ (soumis AVS)", 5036, "+", 1, 1, 0, 0, 1, 0, "", 1, 1, 3, 0, "", "Q"),
            (1410, "Prestation en capital à caractère de prévoyance", 5035, "+", 1, 0, 0, 0, 0, 0, "", 0, 1, 4, 0, "", "S"),
            (1420, "Versement salaire après décès", 5035, "+", 1, 0, 0, 0, 0, 0, "", 0, 1, 4, 0, "", "S"),
            (1500, "Honoraires CA", 5601, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 6, 0, "", "Q"),
            (1900, "Repas gratuit", 5030, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 2.1, 0, "", "R"),
            (1902, "Logement gratuit", 5030, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 2.3, 0, "", "R"),
            (1910, "Part privée voiture de service", 5030, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 2.2, 0, "", "R"),
            (1950, "Réduction loyer logement locatif", 5030, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 2.3, 0, "", "R"),
            (1960, "Droits de participation imposables", 5031, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 5, 0, "", "R"),
            (1961, "Actions de collaborateurs", 5032, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 5, 0, "", "R"),
            (1962, "Options de collaborateurs", 5032, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 5, 0, "", "R"),
            (1971, "Part facultative employeurs IJM", 5740, "+", 1, 0, 0, 0, 0, 0, "", 0, 1, 7, 0, "", "T"),
            (1972, "Part facultative employeurs LPP", 5720, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 7, 0, "", "T"),
            (1973, "Part facultative employeurs rachat LPP", 5721, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 7, 0, "", "T"),
            (1977, "3ème pilier b payé par employeur", 5722, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 7, 0, "", "T"),
            (1978, "3ème pilier a payé par employeur", 5722, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 7, 0, "", "T"),
            (1980, "Perfectionnement (certificat de salaire)", 5034, "+", 1, 0, 0, 0, 0, 0, "", 0, 0, 13.3, 0, "", ""),
            (2000, "Indemnité APG", 2990, "+", 1, 1, 0, 0, 1, 0, "", 0, 1, 1, 0, "Y", ""),
            (2005, "Prestation compensation mil. (CCM)", 2990, "+", 1, 1, 1, 1, 1, 0, "", 0, 1, 1, 0, "Y", ""),
            (2030, "Indemnité journalière accident", 2990, "+", 1, 0, 0, 0, 0, 0, "", 0, 1, 1, 0, "", ""),
            (2035, "Indemnité maladie", 2990, "+", 1, 0, 0, 0, 0, 0, "", 0, 1, 1, 0, "", ""),
            (2050, "Correction indemnité de tiers", 5008, "-", 1, 1, 1, 1, 1, 0, "", 0, 1, 1, 0, "Y", ""),
            (2060, "Déduction RHT/ITP (SM)", 5000, "-", 1, 0, 0, 0, 0, 0, "", 0, 1, 1, 0, "", ""),
            (2065, "Perte de gain RHT/ITP (SH)", "-", "+", 0, 1, 1, 1, 1, 0, "", 1, 0, "", 0, "Y", ""),
            (2070, "Indemnité de chômage", 2990, "+", 1, 0, 0, 0, 0, 0, "", 0, 1, 1, 0, "", ""),
            (2075, "Délai de carence RHT/ITP", 5000, "+", 1, 0, 0, 0, 0, 0, "", 0, 1, 1, 0, "", ""),
            (3000, "Allocation pour enfant", 5040, "+", 1, 0, 0, 0, 0, 0, "", 0, 1, 1, 1, "K", ""),
            (3001, "Paiement pour Allocation pour enfant", 5040, "+", 1, 0, 0, 0, 0, 0, "", 0, 1, 3, 1, "K", ""),
            (3034, "Allocation de naissance", 5040, "+", 1, 0, 0, 0, 0, 0, "", 0, 1, 3, 2, "", "Q"),
            (3035, "Allocation de mariage", 5040, "+", 1, 0, 0, 0, 0, 0, "", 0, 1, 3, 0, "", "Q"),
            (4900, "Compensation net/brut", 5000, "+", 1, 1, 1, 1, 1, 0, "", 1, 1, 7, 0, "", "T"),
            (5000, "Salaire brut", "", "", "", "", "", "", "", "", "", "", "", 8, "", "", ""),
            (5010, "Cotisation AVS", 5700, "-", "", "", "", "", "", "", "", "", "", 9, "", "L", ""),
            (5020, "Cotisation AC", 5701, "-", "", "", "", "", "", "", "", "", "", 9, "", "L", ""),
            (5030, "Cotisation AC complémentaire", 5701, "-", "", "", "", "", "", "", "", "", "", 9, "", "L", ""),
            (5040, "Cotisation AANP", 5730, "-", "", "", "", "", "", "", "", "", "", 9, "", "L", ""),
            (5041, "Cotisation LAAC 11", 5731, "-", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (5042, "Cotisation LAAC 12", 5731, "-", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (5043, "Cotisation LAAC 21", 5731, "-", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (5044, "Cotisation LAAC 22", 5731, "-", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (5045, "Cotisation IJM 11", 5740, "-", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (5046, "Cotisation IJM 12", 5740, "-", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (5047, "Cotisation IJM 21", 5740, "-", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (5048, "Cotisation IJM 22", 5740, "-", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (5050, "Cotisation LPP", 5720, "-", "", "", "", "", "", "", "", "", "", 10.1, "", "M", ""),
            (5051, "Cotisations rachat LPP", 5720, "-", "", "", "", "", "", "", "", "", "", 10.2, "", "", ""),
            (5060, "Montant IS", 5790, "-", "", "", "", "", "", "", "", "", "", 12, "", "", ""),
            (5061, "Montant IS correction", 5790, "-", "", "", "", "", "", "", "", "", "", 12, "", "", ""),
            (5080, "Retenue Part privée voiture de service", 6200, "-", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (5100, "Correction prestations en nature", 2999, "-", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (5110, "Correction avantage en argent", 2999, "-", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (5111, "Compensation cotisations LPP employeur", 2999, "-", "", "", "", "", "", "", "", "", "", 10.1, "", "", ""),
            (5112, "Compensation rachat LPP employeur", 2999, "-", "", "", "", "", "", "", "", "", "", 10.2, "", "", ""),
            (6000, "Frais de voyage", 5820, "+", 0, 0, 0, 0, 0, 0, "", 0, 0, "13.1.1", 0, "", ""),
            (6020, "Frais effectifs expatriés", 5320, "+", 0, 0, 0, 0, 0, 0, "", 0, 0, "13.1.2", 0, "", ""),
            (6035, "Frais forfaitaires pour expatriés", 5320, "+", 0, 0, 0, 0, 0, 0, "", 0, 0, 2.3, 0, "", ""),
            (6040, "Frais forfaitaires de représentation", 5830, "+", 0, 0, 0, 0, 0, 0, "", 0, 0, "13.2.1", 0, "", ""),
            (6050, "Frais forfaitaires de voiture", 5831, "+", 0, 0, 0, 0, 0, 0, "", 0, 0, "13.2.2", 0, "", ""),
            (6070, "Autres frais forfaitaires", 5832, "+", 0, 0, 0, 0, 0, 0, "", 0, 0, "13.2.3", 0, "", ""),
            (6500, "Salaire net", "", "", "", "", "", "", "", "", "", "", "", 11, "", "", ""),
            (6600, "Salaire payé", 1020, "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9010, "Base AVS", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9011, "Salaire AVS", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9012, "Non soumis AVS", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9020, "Base AC", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9021, "Salaire AC", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9022, "Salaire compl. AC", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9023, "Non soumis AC", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9030, "Base LAA", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9031, "Salaire LAA", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9040, "Base LAAC", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9041, "Salaire LAAC 11", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9042, "Salaire LAAC 12", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9043, "Salaire LAAC 21", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9044, "Salaire LAAC 22", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9050, "Base IJM", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9051, "Salaire IJM 11", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9052, "Salaire IJM 12", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9053, "Salaire IJM 21", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9054, "Salaire IJM 22", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9060, "Base LPP", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9061, "Salaire LPP", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9065, "Base IS", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9070, "Salaire IS", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9071, "Salaire IS DT périodique", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9072, "Salaire IS DT apériodique", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9073, "Salaire IS-DT", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9074, "Code tarifaire IS", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
            (9075, "Taux IS", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""),
        ]

        all_rules = self.env.ref('l10n_ch_hr_payroll.hr_payroll_structure_ch_employee_salary').rule_ids
        errors = []
        for rule_data in rules_data:
            l10n_ch_code = str(rule_data[0])
            # LAA/IJM/LAAC rules are not defined over 4 rules
            if l10n_ch_code in ['5042', '5044', '5046', '5048', '9042', '9044', '9052', '9054']:
                continue
            # Only 1 rule for net salary
            if l10n_ch_code == "6600":
                continue
            # Still not covered (LPP/IS)
            if l10n_ch_code in ["9023", "9060", "9061", "9074"]:
                continue
            rule_name = rule_data[1]
            _account_code = rule_data[2]  # YTI Check CoA definition
            _control_system = rule_data[3]  # YTI What is the meaning ?
            l10n_ch_gross_included = bool(rule_data[4])
            l10n_ch_ac_included = bool(rule_data[5])
            l10n_ch_aanp_included = bool(rule_data[6])
            l10n_ch_laac_included = bool(rule_data[7])
            l10n_ch_ijm_included = bool(rule_data[8])
            l10n_ch_lpp_forecast = bool(rule_data[9])
            l10n_ch_lpp_factor = rule_data[10] or 0
            l10n_ch_lpp_retroactive = bool(rule_data[11])
            l10n_ch_source_tax_included = bool(rule_data[12])
            l10n_ch_salary_certificate = str(rule_data[13])
            l10n_ch_caf_statement = str(rule_data[14]) or ""
            l10n_ch_wage_statement = rule_data[15] or ""
            l10n_ch_yearly_statement = rule_data[16] or ""

            salary_rule = all_rules.filtered(lambda r: r.l10n_ch_code == l10n_ch_code)
            if not salary_rule:
                errors.append('Missing rule %s with external code %s' % (rule_name, l10n_ch_code))
                continue
            if len(salary_rule) > 1:
                errors.append('Duplicated rule %s with external code %s' % (rule_name, l10n_ch_code))
                continue
            if salary_rule.l10n_ch_gross_included != l10n_ch_gross_included:
                errors.append("Rule %s: l10n_ch_gross_included - Expected %s - Reality %s" % (l10n_ch_code, l10n_ch_gross_included, salary_rule.l10n_ch_gross_included))
            if salary_rule.l10n_ch_ac_included != l10n_ch_ac_included:
                errors.append("Rule %s: l10n_ch_ac_included - Expected %s - Reality %s" % (l10n_ch_code, l10n_ch_ac_included, salary_rule.l10n_ch_ac_included))
            if salary_rule.l10n_ch_aanp_included != l10n_ch_aanp_included:
                errors.append("Rule %s: l10n_ch_aanp_included - Expected %s - Reality %s" % (l10n_ch_code, l10n_ch_aanp_included, salary_rule.l10n_ch_aanp_included))
            if salary_rule.l10n_ch_laac_included != l10n_ch_laac_included:
                errors.append("Rule %s: l10n_ch_laac_included - Expected %s - Reality %s" % (l10n_ch_code, l10n_ch_laac_included, salary_rule.l10n_ch_laac_included))
            if salary_rule.l10n_ch_ijm_included != l10n_ch_ijm_included:
                errors.append("Rule %s: l10n_ch_ijm_included - Expected %s - Reality %s" % (l10n_ch_code, l10n_ch_ijm_included, salary_rule.l10n_ch_ijm_included))
            if salary_rule.l10n_ch_lpp_forecast != l10n_ch_lpp_forecast:
                errors.append("Rule %s: l10n_ch_lpp_forecast - Expected %s - Reality %s" % (l10n_ch_code, l10n_ch_lpp_forecast, salary_rule.l10n_ch_lpp_forecast))
            if salary_rule.l10n_ch_lpp_factor != l10n_ch_lpp_factor:
                errors.append("Rule %s: l10n_ch_lpp_factor - Expected %s - Reality %s" % (l10n_ch_code, l10n_ch_lpp_factor, salary_rule.l10n_ch_lpp_factor))
            if salary_rule.l10n_ch_lpp_retroactive != l10n_ch_lpp_retroactive:
                errors.append("Rule %s: l10n_ch_lpp_retroactive - Expected %s - Reality %s" % (l10n_ch_code, l10n_ch_lpp_retroactive, salary_rule.l10n_ch_lpp_retroactive))
            if salary_rule.l10n_ch_source_tax_included != l10n_ch_source_tax_included:
                errors.append("Rule %s: l10n_ch_source_tax_included - Expected %s - Reality %s" % (l10n_ch_code, l10n_ch_source_tax_included, salary_rule.l10n_ch_source_tax_included))
            if (salary_rule.l10n_ch_salary_certificate or l10n_ch_salary_certificate) and salary_rule.l10n_ch_salary_certificate != l10n_ch_salary_certificate:
                errors.append("Rule %s: l10n_ch_salary_certificate - Expected %s - Reality %s" % (l10n_ch_code, l10n_ch_salary_certificate, salary_rule.l10n_ch_salary_certificate))
            if (salary_rule.l10n_ch_caf_statement or l10n_ch_caf_statement) and salary_rule.l10n_ch_caf_statement != l10n_ch_caf_statement:
                errors.append("Rule %s: l10n_ch_caf_statement - Expected %s - Reality %s" % (l10n_ch_code, l10n_ch_caf_statement, salary_rule.l10n_ch_caf_statement))
            if (l10n_ch_wage_statement or salary_rule.l10n_ch_wage_statement) and salary_rule.l10n_ch_wage_statement != l10n_ch_wage_statement:
                errors.append("Rule %s: l10n_ch_wage_statement - Expected %s - Reality %s" % (l10n_ch_code, l10n_ch_wage_statement, salary_rule.l10n_ch_wage_statement))
            if (l10n_ch_yearly_statement or salary_rule.l10n_ch_yearly_statement) and salary_rule.l10n_ch_yearly_statement != l10n_ch_yearly_statement:
                errors.append("Rule %s: l10n_ch_yearly_statement - Expected %s - Reality %s" % (l10n_ch_code, l10n_ch_yearly_statement, salary_rule.l10n_ch_yearly_statement))
        self.assertFalse(errors, '\n'.join(errors))
