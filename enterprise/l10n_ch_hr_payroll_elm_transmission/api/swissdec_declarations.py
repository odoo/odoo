from collections import defaultdict
from copy import deepcopy
import datetime
from odoo import fields
from odoo.tools.misc import format_date, file_path
from odoo.tools.float_utils import float_round
import re
import uuid


SALARY_TYPE_MAPPING = {
    "AHV-AVS-Salaries": "AHV-AVS-Salary",
    "FAK-CAF-Salaries": "FAK-CAF-Salary",
    "UVG-LAA-Salaries": "UVG-LAA-Salary",
    "UVGZ-LAAC-Salaries": "UVGZ-LAAC-Salary",
    "KTG-AMC-Salaries": "KTG-AMC-Salary",
    "BVG-LPP-Salaries": "BVG-LPP-Salary",
    "TaxCrossborderSalaries": "TaxCrossborderSalary",
    "TaxSalaries": "TaxSalary",
    "TaxAtSourceSalaries": "TaxAtSourceSalary",
    "StatisticSalaries": "StatisticSalary"
}
XSD_SKIP_VALUE = "XSDSKIP"

INSTITUTION_MODEL_MAPPING = {
    "l10n.ch.social.insurance": "AHV-AVS",
    "l10n.ch.compensation.fund": "FAK-CAF",
    "l10n.ch.sickness.insurance": "KTG-AMC",
    "l10n.ch.accident.insurance": "UVG-LAA",
    "l10n.ch.additional.accident.insurance": "UVGZ-LAAC",
    "l10n.ch.lpp.insurance": "BVG-LPP",
    "l10n.ch.location.unit": "TaxCrossborder",
    "l10n.ch.source.tax.institution": "TaxAtSource",
    "BFS": "Statistic",
    "Tax": "Tax"
}

MAPPED_DOMAIN_IDENTIFICATION = {
    "AHV-AVS": "AHV-AVS-Identification",
    "FAK-CAF": "FAK-CAF-Identification",
    "UVG-LAA": "UVG-LAA-Identification",
    "UVGZ-LAAC": "UVGZ-LAAC-Identification",
    "KTG-AMC": "KTG-AMC-Identification",
    "BVG-LPP": "BVG-LPP-Identification",
    "Tax": "TaxIdentification",
    "TaxAtSource": "TaxAtSourceIdentification",
    "TaxCrossborder": "TaxCrossborderIdentification",
    "Statistic": "StatisticIdentification"
}

IS_REASON_MAPPING = {
    'entryCompany': ('Entry', 'entryCompany'),
    'entryCanton': ('Entry', 'cantonChange'),
    'entryOther': ('Entry', 'entryOther'),
    'withdrawalCompany': ('Withdrawal', 'withdrawalCompany'),
    'withdrawalNat': ('Withdrawal', 'naturalization'),
    'withdrawalSettled': ('Withdrawal', 'settled-C'),
    'withdrawalCanton': ('Withdrawal', 'cantonChange'),
    'withdrawalOther': ('Withdrawal', 'others'),
    'civilstate': ('Mutation', 'civilstate'),
    'partnerWork': ('Mutation', 'partnerWork'),
    'partnerWorkplaceChangeCHAbroad': ('Mutation', 'partnerWorkplaceChangeCHAbroad'),
    'residence': ('Mutation', 'residence'),
    'childrenDeduction': ('Mutation', 'childrenDeduction'),
    'churchTax': ('Mutation', 'churchTax'),
    'others': ('Mutation', 'others')
}


IS_CODE_PATTERN = r"^[ABCDEFGHLNMPQRSTU][0-9][YN]$"

missing_value = "XSDMISSING"
XSD_YMONTH = "XSDGYEARMONTH"


class SwissdecInstitution:
    def __init__(self, institution, pay_agreement=None, payroll_unit=None):
        if institution:
            assert isinstance(institution, str)
        if pay_agreement:
            assert isinstance(pay_agreement, str)
        if payroll_unit:
            assert isinstance(payroll_unit, str)
        self._name = institution
        self.pay_agreement = pay_agreement
        self.payroll_unit = payroll_unit


class SwissdecDeclaration:
    """
    Helper Class to Display and perform operations on Swissdec declare salary objects
    documentation : https://www.swissdec.ch/fr/elm
    """

    @staticmethod
    def amount2str(amount):
        return "{:.2f}".format(amount)

    def create_ahv_avs_ema(self, institution_id, declaration_category, valid_as_of, month, year, acc_from, acc_until, ceo_rel=False):
        ema = {
            "institutionIDRef": self.get_institution_id_ref(institution_id),
            "DeclarationCategory": {
                declaration_category: {"ValidAsOf": valid_as_of}
            },
            "AccountingTime": {
                "from": acc_from,
                "until": acc_until,
            },
            "AHV-AVS-Income": "0.00",
            "ALV-AC-Income": "0.00"
        }
        if ceo_rel:
            ema["DegreeOfRelationship"] = ceo_rel
        return ema

    def create_ahv_avs_salary(self, institution_id, accounting_from, accounting_to, avs_salary, ac_salary, acc_salary, avs_open, ac_open, splits, ceo_rel=False):
        if not (avs_salary or ac_salary or acc_salary or avs_open or ac_open):
            return False

        avs_salaries = {
            "AHV-AVS-Income": self.amount2str(avs_salary),
            "ALV-AC-Income": self.amount2str(ac_salary)
        }

        if acc_salary:
            avs_salaries["ALVZ-ACS-Income"] = self.amount2str(acc_salary)
        if avs_open:
            avs_salaries["AHV-AVS-Open"] = self.amount2str(avs_open)
        if ac_open:
            avs_salaries["ALV-AC-Open"] = self.amount2str(ac_open)
        if ceo_rel:
            avs_salaries["DegreeOfRelationship"] = ceo_rel
        if splits:
            if splits.additional_delivery_date:
                income_splits = {
                    "AdditionalDeliveryDate": format_date(splits.env, splits.additional_delivery_date, date_format='yyyy-MM-dd'),
                }
            else:
                income_splits = {
                    "Splits": [{
                        "SplitCurrentYearIncome": self.amount2str(splits.income_to_split - sum(splits.avs_split_lines.mapped('income'))),
                        "SplitPreviousYear": {
                            "Period": {
                                "from": format_date(line.env, line.date_from, date_format='yyyy-MM-dd'),
                                "until": format_date(line.env, line.date_to, date_format='yyyy-MM-dd'),
                            },
                            "Income": self.amount2str(line.income)
                        }
                    } for line in splits.avs_split_lines]
                }
            avs_salaries["AHV-AVS-IncomeSplits"] = income_splits


        return {
            "institutionIDRef": self.get_institution_id_ref(institution=institution_id),
            "AccountingTime": {
                "from": accounting_from,
                "until": accounting_to,
            },
            **avs_salaries
        }

    def create_fak_caf_ema(self, institution_id, canton, declaration_category, valid_as_of, reason, period_from, period_until):
        return {
            "institutionIDRef": self.get_institution_id_ref(institution_id),
            "DeclarationCategory": {
                declaration_category: {
                    "ValidAsOf": valid_as_of,
                    "Reason": reason
                },
            },
            "FAK-CAF-Period": {
                "from": period_from,
                "until": period_until,
            },
            "FAK-CAF-ContributorySalary": "0.00",
            "FAK-CAF-WorkplaceCanton": canton
        }

    def create_bvg_lpp_ema(self, institution_id, declarations, codes, bvg_lpp_annual_basis):

        declaration_category = {}
        if declarations.get("Entry"):
            declaration_category["Entry"] = declarations.get("Entry")
        if declarations.get("Withdrawal"):
            declaration_category["Withdrawal"] = declarations.get("Withdrawal")
        if declarations.get("Mutation"):
            declaration_category["Mutation"] = declarations.get("Mutation")


        ema = {
            "institutionIDRef": self.get_institution_id_ref(institution_id),
            "BVG-LPP-AnnualBasis": self.amount2str(bvg_lpp_annual_basis),
        }

        if declaration_category:
            ema["DeclarationCategory"] = declaration_category

        if codes:
            ema["BVG-LPP-Code"] = codes[0]

        return ema

    @staticmethod
    def source_tax_ema_to_dict(st_ema_objects):
        declaration_category = {}
        for ema in st_ema_objects:
            ema_declaration_category, reason = IS_REASON_MAPPING[ema.reason]
            declaration_category[ema_declaration_category] = declaration_category.get(
                ema_declaration_category, []) + [{"Reason": reason, "ValidAsOf": format_date(ema.env, ema.valid_as_of,
                                                                                             date_format='yyyy-MM-dd')}]
        if declaration_category:
            return {
                "DeclarationCategory": declaration_category
            }
        else:
            return {}

    @staticmethod
    def get_salary_tag_counter(staff):
        counters = {
            ("NumberOf-AHV-AVS-Salary-Tags", "AHV-AVS-Salaries"): 0,
            ("NumberOf-FAK-CAF-Salary-Tags", "FAK-CAF-Salaries"): 0,
            ("NumberOf-UVG-LAA-Salary-Tags", "UVG-LAA-Salaries"): 0,
            ("NumberOf-UVGZ-LAAC-Salary-Tags", "UVGZ-LAAC-Salaries"): 0,
            ("NumberOf-BVG-LPP-Salary-Tags", "BVG-LPP-Salaries"): 0,
            ("NumberOf-KTG-AMC-Salary-Tags", "KTG-AMC-Salaries"): 0,
            ("NumberOf-TaxSalary-Tags", "TaxSalaries"): 0,
            ("NumberOf-TaxCrossborderSalary-Tags", "TaxCrossborderSalaries"): 0,
            ("NumberOf-TaxAtSourceSalary-Tags", "TaxAtSourceSalaries"): 0,
            ("NumberOf-StatisticSalary-Tags", "StatisticSalaries"): 0
        }

        for person in staff["Staff"]["Person"]:
            for tag in counters:
                if tag[1] in person:
                    counters[tag] += len(person[tag[1]][SALARY_TYPE_MAPPING[tag[1]]])
        return {
            tag[0]: counters[tag] for tag in counters if counters[tag] > 0
        }

    @staticmethod
    def _reverse_is_code_type(is_code):
        if is_code:
            if is_code in ['NON', 'NOY', 'HEN', 'HEY', 'MEN', 'MEY', 'SFN']:
                return "CategoryPredefined"
            elif re.match(IS_CODE_PATTERN, is_code):
                return "TaxAtSourceCode"
            else:
                return "CategoryOpen"
        else:
            return "CategoryPredefined"

    @staticmethod
    def _round_to_5_cents(total):
        total = float_round(total, precision_rounding=0.01, rounding_method="HALF-UP")
        remainder = total % 0.05
        if remainder >= 0.025:
            result = total + 0.05 - remainder
        else:
            result = total - remainder
        return SwissdecDeclaration.amount2str(result)

    @staticmethod
    def get_salary_totals(staff, **kwargs):
        def convert_floats_to_str(data):
            for key, value in data.items():
                if key != "CurrentMonth" and key != "Month":
                    if isinstance(value, float):
                        data[key] = SwissdecDeclaration.amount2str(value)
                    elif isinstance(value, dict):
                        convert_floats_to_str(value)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                convert_floats_to_str(item)
                else:
                    data[key] = value

        salary_totals = dict()
        avs_totals = defaultdict(lambda: {
            "Total-AHV-AVS-Incomes": 0,
            "Total-AHV-AVS-Open": 0,
            "Total-ALV-AC-Incomes": 0,
            "Total-ALVZ-ACS-Incomes": 0,
            "Total-ALV-AC-Open": 0,
        })

        # Institution - Canton - Totals
        fak_totals = defaultdict(lambda: defaultdict(lambda: {
            "Total-FAK-CAF-ContributorySalary": 0,
            "Total-FAK-CAF-FamilyIncomeSupplement": 0,
        }))

        # Institution - Branch - Sex - Code
        uvg_totals = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float))))
        uvg_gender_totals = defaultdict(lambda: {
            "F": set(),
            "M": set()
        })

        # Institution - Code - Sex - Total
        uvgz_totals = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

        # Institution - Code - Sex - Total
        ijm_totals = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

        # QST
        source_tax_totals = defaultdict(lambda: {
            "TotalTaxableEarning": "0.00",
            "TotalTaxAtSource": "0.00",
            "TotalCommission": "0.00",
            "CurrentMonth": kwargs.get("CurrentMonth", False)
        })
        # QST - month
        source_tax_correction_totals = defaultdict(lambda: defaultdict(lambda: {
            "TotalTaxableEarning": "0.00",
            "TotalTaxAtSource": "0.00",
            "TotalCommission": "0.00",
        }))

        source_tax_commission_rates = kwargs.get("source_tax_commission_rates", defaultdict(float))

        # Txb totals: QST - Taxable earning

        txb_totals = defaultdict(lambda: defaultdict())

        for person in staff:
            particular = person.get("Particulars", {})
            sex = particular["Sex"]
            for avs_salary in person.get("AHV-AVS-Salaries", {}).get("AHV-AVS-Salary", []):
                avs_totals[avs_salary["institutionIDRef"]]["Total-AHV-AVS-Incomes"] += float(avs_salary.get("AHV-AVS-Income", 0))
                avs_totals[avs_salary["institutionIDRef"]]["Total-AHV-AVS-Open"] += float(avs_salary.get("AHV-AVS-Open", 0))
                avs_totals[avs_salary["institutionIDRef"]]["Total-ALV-AC-Incomes"] += float(avs_salary.get("ALV-AC-Income", 0))
                avs_totals[avs_salary["institutionIDRef"]]["Total-ALVZ-ACS-Incomes"] += float(avs_salary.get("ALVZ-ACS-Income", 0))
                avs_totals[avs_salary["institutionIDRef"]]["Total-ALV-AC-Open"] += float(avs_salary.get("ALV-AC-Open", 0))

            for caf_salary in person.get("FAK-CAF-Salaries", {}).get("FAK-CAF-Salary", []):
                fak_totals[caf_salary["institutionIDRef"]][caf_salary["FAK-CAF-WorkplaceCanton"]]["Total-FAK-CAF-ContributorySalary"] += float(caf_salary.get("FAK-CAF-ContributorySalary", 0))
                fak_totals[caf_salary["institutionIDRef"]][caf_salary["FAK-CAF-WorkplaceCanton"]]["Total-FAK-CAF-FamilyIncomeSupplement"] += float(caf_salary.get("FAK-CAF-FamilyIncomeSupplement", {}).get("FAK-CAF-FamilyIncomeSupplementPerPerson", 0))

            for uvg_salary in person.get("UVG-LAA-Salaries", {}).get("UVG-LAA-Salary", []):
                if kwargs.get("uvg_month", False) >= 9:
                    current_valid_from = uvg_salary.get("AccountingTime", {}).get("from", False)
                    current_valid_until = uvg_salary.get("AccountingTime", {}).get("until", False)
                    if current_valid_from and current_valid_until:
                        valid_from_date_time = fields.Date.from_string(current_valid_from)
                        valid_until_date_time = fields.Date.from_string(current_valid_until)
                        current_withdrawal = person.get("Work", {}).get("WithdrawalDate", False)
                        current_withdrawal_date_time = fields.Date.from_string(current_withdrawal) if current_withdrawal else False
                        end_of_september = datetime.date(kwargs.get("uvg_year", valid_from_date_time.year), 9, 30)
                        if valid_from_date_time <= end_of_september and valid_until_date_time >= end_of_september and (not current_withdrawal_date_time or current_withdrawal_date_time > end_of_september):
                            uvg_gender_totals[uvg_salary["institutionIDRef"]][sex].add(person["Particulars"]["EmployeeNumber"])
                uvg_totals[uvg_salary["institutionIDRef"]][uvg_salary["UVG-LAA-Code"][0]][sex][uvg_salary["UVG-LAA-Code"][1]] += float(uvg_salary.get("UVG-LAA-ContributorySalary", 0))

            for uvgz_salary in person.get("UVGZ-LAAC-Salaries", {}).get("UVGZ-LAAC-Salary", []):
                uvgz_totals[uvgz_salary["institutionIDRef"]][uvgz_salary["UVGZ-LAAC-Code"]][sex] += float(uvgz_salary.get("UVGZ-LAAC-ContributorySalary", 0))

            for ijm_salary in person.get("KTG-AMC-Salaries", {}).get("KTG-AMC-Salary", []):
                ijm_totals[ijm_salary["institutionIDRef"]][ijm_salary["KTG-AMC-Code"]][sex] += float(ijm_salary.get("KTG-AMC-ContributorySalary", 0))

            for qst_salary in person.get("TaxAtSourceSalaries", {}).get("TaxAtSourceSalary", []):
                qst_id_ref = qst_salary["institutionIDRef"]
                current_taxable_earning = float(source_tax_totals[qst_id_ref]["TotalTaxableEarning"])
                current_tax_at_souce = float(source_tax_totals[qst_id_ref]["TotalTaxAtSource"])
                source_tax_totals[qst_id_ref]["TotalTaxableEarning"] = SwissdecDeclaration.amount2str(current_taxable_earning + float(qst_salary.get("Current", {}).get("TaxableEarning", 0)))
                source_tax_totals[qst_id_ref]["TotalTaxAtSource"] = SwissdecDeclaration.amount2str(current_tax_at_souce + float(qst_salary.get("Current", {}).get("TaxAtSource", 0)))

                for correction in qst_salary.get("Correction", []):
                    month = tuple(correction["Month"])
                    new = correction.get("New", dict())
                    old = correction.get("Old", dict())
                    for key, value in new.items():
                        total_key = f"Total{key}"
                        if total_key in source_tax_correction_totals[qst_id_ref][month]:
                            source_tax_correction_totals[qst_id_ref][month][total_key] = SwissdecDeclaration.amount2str(float(source_tax_correction_totals[qst_id_ref][month][total_key]) + float(value))
                    for key, value in old.items():
                        total_key = f"Total{key}"
                        if total_key in source_tax_correction_totals[qst_id_ref][month]:
                            source_tax_correction_totals[qst_id_ref][month][total_key] = SwissdecDeclaration.amount2str(float(source_tax_correction_totals[qst_id_ref][month][total_key]) + float(value))
                for correction in qst_salary.get("CorrectionConfirmed", []):
                    month = tuple(correction["Month"])
                    for key, value in correction.items():
                        if key != "Month":
                            total_key = f"Total{key}"
                            if total_key in source_tax_correction_totals[qst_id_ref][month]:
                                source_tax_correction_totals[qst_id_ref][month][total_key] = SwissdecDeclaration.amount2str(float(source_tax_correction_totals[qst_id_ref][month][total_key]) + float(value))

            for qst_institution in source_tax_totals:
                source_tax_totals[qst_institution]['TotalCommission'] = SwissdecDeclaration._round_to_5_cents(total=float(source_tax_totals[qst_institution]['TotalTaxAtSource']) * source_tax_commission_rates[qst_institution])

            for qst_institution in source_tax_correction_totals:
                for month in source_tax_correction_totals[qst_institution]:
                    source_tax_correction_totals[qst_institution][month]['TotalCommission'] = SwissdecDeclaration._round_to_5_cents(total=float(source_tax_correction_totals[qst_institution][month]['TotalTaxAtSource']) * source_tax_commission_rates[qst_institution])

            global_txb_period = kwargs.get("global_txb_periods", {})
            for txb_salary in person.get("TaxCrossborderSalaries", {}).get("TaxCrossborderSalary", []):
                existing_txb = txb_totals[txb_salary["institutionIDRef"]]
                if existing_txb:
                    current_from = global_txb_period[int(existing_txb["Period"]["from"].split("-")[0])]["from"]
                    current_until = global_txb_period[int(existing_txb["Period"]["until"].split("-")[0])]["until"]
                    if txb_salary["Period"]["from"] > current_from:
                        txb_totals[txb_salary["institutionIDRef"]]["Period"]["from"] = current_from
                    if txb_salary["Period"]["until"] < current_until:
                        txb_totals[txb_salary["institutionIDRef"]]["Period"]["until"] = current_until
                else:
                    txb_totals[txb_salary["institutionIDRef"]]["Period"] = {
                        "from": global_txb_period[int(txb_salary["Period"]["from"].split('-')[0])]["from"],
                        "until": global_txb_period[int(txb_salary["Period"]["from"].split('-')[0])]["until"]
                    }
                    txb_totals[txb_salary["institutionIDRef"]]["TaxableEarning"] = "0.00"
                    txb_totals[txb_salary["institutionIDRef"]]["TaxAtSourceCanton"] = txb_salary["TaxAtSourceCanton"]

                txb_totals[txb_salary["institutionIDRef"]]["TaxableEarning"] = SwissdecDeclaration.amount2str(float(txb_salary.get("TaxableEarning", "0.00")) + float(txb_totals[txb_salary["institutionIDRef"]]["TaxableEarning"]))


        qst_totals = []
        for institution in source_tax_totals:
            qst_total = {
                "TotalMonth": source_tax_totals[institution],
                "institutionIDRef": institution
            }
            if source_tax_correction_totals[institution]:
                qst_total["CorrectionMonth"] = sorted([{"Month": corr_month, **source_tax_correction_totals[institution][corr_month]} for corr_month in source_tax_correction_totals[institution]], key=lambda corr_d: (corr_d["Month"][1], corr_d["Month"][2]))
            qst_totals.append(qst_total)

        txb_totals_l = [{"institutionIDRef": institution, **txb_totals[institution]} for institution in txb_totals]

        ahv_total = [{
            **{key: SwissdecDeclaration.amount2str(avs_totals[institution][key]) for key in avs_totals[institution]},
            "institutionIDRef": institution
        } for institution in avs_totals]

        fak_caf_totals = [
            {
                "institutionIDRef": institution,
                "Total-FAK-CAF-PerCanton": [
                    {
                        "Canton": canton,
                        **{
                            key: SwissdecDeclaration.amount2str(fak_totals[institution][canton].get(key, 0))
                            for key in fak_totals[institution][canton]
                        },
                    } for canton in fak_totals[institution]
                ]
            }
            for institution in fak_totals
        ]
        if ahv_total:
            salary_totals["AHV-AVS-Totals"] = ahv_total

        if fak_caf_totals:
            salary_totals["FAK-CAF-Totals"] = fak_caf_totals

        uvg_laa_totals = []
        for institution in uvg_totals:
            result = {
                "institutionIDRef": institution,
                "UVG-LAA-BranchTotals": {
                    "UVG-LAA-BranchTotal": []
                },
                "UVG-LAA-MasterTotal": 0.0,
                "NumberOfFemalePersons": 0,
                "NumberOfMalePersons": 0
            }
            master_total = 0.0
            female_count = 0
            male_count = 0

            # Iterate over branches and gender totals in `uvg_totals`
            for branch, genders in uvg_totals[institution].items():
                branch_total = {
                    "BranchIdentifier": branch,
                    "Female-Totals": {"NBU-BU-ANP-AP-Total": 0.0, "BU-AP-Total": 0.0},
                    "Male-Totals": {"NBU-BU-ANP-AP-Total": 0.0, "BU-AP-Total": 0.0}
                }

                for gender, codes in genders.items():
                    gender_totals = {"NBU-BU-ANP-AP-Total": 0.0, "BU-AP-Total": 0.0}

                    for code, amount in codes.items():
                        if code in ["1", "2"]:  # Map to NBU-BU-ANP-AP-Total
                            gender_totals["NBU-BU-ANP-AP-Total"] += amount
                        elif code == "3":  # Map to BU-AP-Total
                            gender_totals["BU-AP-Total"] += amount

                    # Add gender totals to branch totals
                    if gender == "F":
                        branch_total["Female-Totals"] = gender_totals
                        female_count += 1
                    elif gender == "M":
                        branch_total["Male-Totals"] = gender_totals
                        male_count += 1

                    # Accumulate to master total
                    master_total += sum(gender_totals.values())

                # Append the branch total to the branch totals list
                result["UVG-LAA-BranchTotals"]["UVG-LAA-BranchTotal"].append(branch_total)

            # Populate master total and counts
            result["UVG-LAA-MasterTotal"] = master_total
            result["NumberOfFemalePersons"] = len(uvg_gender_totals[institution]["F"])
            result["NumberOfMalePersons"] = len(uvg_gender_totals[institution]["M"])
            convert_floats_to_str(result)
            uvg_laa_totals.append(deepcopy(result))

        uvgz_laac_totals = []
        for institution in uvgz_totals:
            result = {
                "institutionIDRef": institution,
                "UVGZ-LAAC-CategoryTotals": {
                    "UVGZ-LAAC-CategoryTotal": []
                },
                "UVGZ-LAAC-MasterTotal": 0.0
            }

            # Variable to accumulate the master total
            master_total = 0.0

            # Iterate over categories and gender totals in `uvgz_totals`
            for category_code, genders in uvgz_totals[institution].items():
                # Initialize totals for the current category
                category_total = {
                    "CategoryCode": category_code,
                    "Female-Total": 0.0,
                    "Male-Total": 0.0
                }

                # Calculate totals for each gender
                for gender, total in genders.items():
                    if gender == "F":
                        category_total["Female-Total"] += total
                    elif gender == "M":
                        category_total["Male-Total"] += total

                # Add category totals to the master total
                master_total += category_total["Female-Total"] + category_total["Male-Total"]

                # Append category total to the category totals list
                result["UVGZ-LAAC-CategoryTotals"]["UVGZ-LAAC-CategoryTotal"].append(category_total)

            # Set the master total in the result
            result["UVGZ-LAAC-MasterTotal"] = master_total
            convert_floats_to_str(result)
            uvgz_laac_totals.append(deepcopy(result))

        ktg_amc_totals = []
        for institution in ijm_totals:
            result = {
                "institutionIDRef": institution,
                "KTG-AMC-CategoryTotals": {
                    "KTG-AMC-CategoryTotal": []
                },
                "KTG-AMC-MasterTotal": 0.0
            }

            # Variable to accumulate the master total
            master_total = 0.0

            # Iterate over categories and gender totals in `uvgz_totals`
            for category_code, genders in ijm_totals[institution].items():
                # Initialize totals for the current category
                category_total = {
                    "CategoryCode": category_code,
                    "Female-Total": 0.0,
                    "Male-Total": 0.0
                }

                # Calculate totals for each gender
                for gender, total in genders.items():
                    if gender == "F":
                        category_total["Female-Total"] += total
                    elif gender == "M":
                        category_total["Male-Total"] += total

                # Add category totals to the master total
                master_total += category_total["Female-Total"] + category_total["Male-Total"]

                # Append category total to the category totals list
                result["KTG-AMC-CategoryTotals"]["KTG-AMC-CategoryTotal"].append(category_total)

            # Set the master total in the result
            result["KTG-AMC-MasterTotal"] = master_total
            convert_floats_to_str(result)
            ktg_amc_totals.append(deepcopy(result))


        if uvg_laa_totals:
            salary_totals["UVG-LAA-Totals"] = uvg_laa_totals

        if uvgz_laac_totals:
            salary_totals["UVGZ-LAAC-Totals"] = uvgz_laac_totals

        if ktg_amc_totals:
            salary_totals["KTG-AMC-Totals"] = ktg_amc_totals

        if qst_totals:
            salary_totals["TaxAtSourceTotals"] = qst_totals

        if txb_totals_l:
            salary_totals["TaxCrossborderTotals"] = txb_totals_l

        return salary_totals

    def get_instution_description(self, institution, **kwargs):
        description = {}
        if INSTITUTION_MODEL_MAPPING[institution._name] == "AHV-AVS":
            description = {
                "AK-CC-BranchNumber": institution.insurance_code,
                "AK-CC-CustomerNumber": institution.member_number,
            }

            if not kwargs.get('skip_id_ref', False):
                if institution.laa_insurance_id:
                    uvg_laa = {
                        "Name": institution.laa_insurance_id.name,
                        "ValidAsOf": format_date(institution.env, institution.laa_insurance_from,
                                                 date_format='yyyy-MM-dd')
                    }
                    if institution.laa_insurance_id.uid_bfs_number:
                        uvg_laa["UID-BFS"] = {
                            "UID": institution.laa_insurance_id.uid_bfs_number
                        }
                    else:
                        uvg_laa["UID-BFS"] = {
                            "Unknown": XSD_SKIP_VALUE
                        }
                else:
                    uvg_laa = {
                        "NoneWithReason": institution.no_laa_reason
                    }

                if institution.lpp_insurance_id:
                    bvg_lpp = {
                        "Name": institution.lpp_insurance_id.name,
                        "ValidAsOf": format_date(institution.env, institution.lpp_insurance_from,
                                                 date_format='yyyy-MM-dd')
                    }
                    if institution.lpp_insurance_id.uid_bfs:
                        bvg_lpp["UID-BFS"] = {
                            "UID": institution.lpp_insurance_id.uid_bfs
                        }
                    else:
                        bvg_lpp["UID-BFS"] = {
                            "Unknown": XSD_SKIP_VALUE
                        }
                else:
                    bvg_lpp = {
                        "NoneWithReason": institution.no_lpp_reason
                    }
                description.update({
                    "UVG-LAA-Insurance": uvg_laa,
                    "BVG-LPP-Insurance": bvg_lpp
                })

            if institution.member_subnumber:
                description["AK-CC-SubNumber"] = institution.member_subnumber

        elif INSTITUTION_MODEL_MAPPING[institution._name] == "FAK-CAF":
            description = {
                "FAK-CAF-BranchNumber": institution.insurance_code,
                "FAK-CAF-CustomerNumber": institution.member_number,
            }
            if institution.member_subnumber:
                description["FAK-CAF-SubNumber"] = institution.member_subnumber

        elif INSTITUTION_MODEL_MAPPING[institution._name] == "BVG-LPP":
            description = {
                "InsuranceID": institution.insurance_code,
                "InsuranceCompanyName": institution.name,
                "CustomerIdentity": institution.customer_number,
                "ContractIdentity": institution.contract_number,
            }
            if not kwargs.get('skip_id_ref', False):
                description["GeneralValidAsOf"] = kwargs.get("general_validasof", missing_value)

            if institution.fund_number:
                description["PayrollUnit"] = institution.fund_number

        elif INSTITUTION_MODEL_MAPPING[institution._name] in ["UVG-LAA", "KTG-AMC", "UVGZ-LAAC"]:

            description = {
                "InsuranceID": institution.insurance_code,
                "InsuranceCompanyName": institution.name,
                "CustomerIdentity": institution.customer_number,
                "ContractIdentity": institution.contract_number,
            }
            if kwargs.get("incomplete_declaration", False):
                description['DeclarationIncomplete'] = [XSD_SKIP_VALUE]

        elif INSTITUTION_MODEL_MAPPING[institution._name] == "TaxCrossborder":
            description = {
                "CantonID": institution.canton,
                "CustomerIdentity": institution.dpi_number,
            }
            """
            todo: still
            if institution.company_number:
                txb["PayrollUnit"] = institution.company_number
            return txb
            """
        elif INSTITUTION_MODEL_MAPPING[institution._name] == "TaxAtSource":
            description = {
                "CantonID": institution.canton,
                "CustomerIdentity": institution.dpi_number,
            }

            if institution.company_number:
                description["PayrollUnit"] = institution.company_number

        elif INSTITUTION_MODEL_MAPPING[institution._name] == "Statistic":
            description = {
                "PayAgreement": institution.pay_agreement
            }
            if institution.payroll_unit:
                description["PayrollUnit"] = institution.payroll_unit

        if not kwargs.get('skip_id_ref', False):
            description["institutionID"] = self.get_institution_id_ref(institution)

        return description

    def get_workplace_id_ref(self, workplace):
        workplace_id_ref = f"{workplace.bur_ree_number or workplace.in_house_id or workplace.id}"
        return f"#W_{workplace_id_ref}"

    def get_workplace_working_hours(self, workplace):
        workplace_id_ref = self.get_workplace_id_ref(workplace)
        if workplace.weekly_hours > 0 and workplace.weekly_lessons == 0:
            return {
                "WeeklyHours": {
                    "_value_1": self.amount2str(workplace.weekly_hours),
                    "companyWeeklyHoursID": f"#WT_{workplace_id_ref}"
                }
            }
        elif workplace.weekly_hours == 0 and workplace.weekly_lessons > 0:
            return {
                "WeeklyLessons": {
                    "_value_1": self.amount2str(workplace.weekly_lessons),
                    "companyWeeklyLessonsID": f"#WT_{workplace_id_ref}"
                }
            }
        elif workplace.weekly_hours > 0 and workplace.weekly_lessons > 0:
            return {
                "WeeklyHoursAndLessons": {
                    "WeeklyHours": self.amount2str(workplace.weekly_hours),
                    "WeeklyLessons": self.amount2str(workplace.weekly_lessons),
                    "companyWeeklyHoursAndLessonsID": f"#WT_{workplace_id_ref}"
                },
            }
        else:
            return missing_value

    def get_institution_id_ref(self, institution):
        if institution:
            if INSTITUTION_MODEL_MAPPING[institution._name] not in ["FAK-CAF", "TaxCrossborder", "TaxAtSource", "Tax", "Statistic"]:
                return f"#{INSTITUTION_MODEL_MAPPING.get(institution._name)}_{institution.insurance_code}"
            elif INSTITUTION_MODEL_MAPPING[institution._name] == "FAK-CAF":
                return f"#{INSTITUTION_MODEL_MAPPING.get(institution._name)}_{institution.insurance_code}_{institution.member_number}"
            elif INSTITUTION_MODEL_MAPPING[institution._name] == "TaxCrossborder":
                return f"#{INSTITUTION_MODEL_MAPPING.get(institution._name)}_{institution.canton}"
            elif INSTITUTION_MODEL_MAPPING[institution._name] == "TaxAtSource":
                return f"#QST_{institution.canton}"
            elif INSTITUTION_MODEL_MAPPING[institution._name] in ["Tax", "Statistic"]:
                return f"#{institution._name}"
        else:
            return False
    
    def get_institution_job(self, institution):
        return {
            "institutionIDRef": self.get_institution_id_ref(institution),
            "ProcessByDistributor": "true"
        }

    def get_institutions(self, institutions, **kwargs):
        institution_description = {}
        for institution in institutions:
            institution_type = INSTITUTION_MODEL_MAPPING.get(institution._name, False)
            if institution._name == "l10n.ch.source.tax.institution":
                if kwargs.get("txb", False):
                    institution_type = "TaxCrossborder"
            if institution_type and institution_type not in ["Tax", "Statistic"]:
                if institution_type in institution_description:
                    institution_description[institution_type].append(self.get_instution_description(institution, **kwargs))
                else:
                    institution_description[institution_type] = [self.get_instution_description(institution, **kwargs)]
            elif institution_type == "Statistic":
                institution_description[institution_type] = self.get_instution_description(institution, **kwargs)

        return {
            "Institutions": institution_description
        }

    def get_mapped_institution_descriptions(self, institutions, **kwargs):
        institution_description = dict()
        for institution in institutions:
            id_ref = self.get_institution_id_ref(institution)
            institution_description[id_ref] = self.get_instution_description(institution, skip_id_ref=True, **kwargs)

        return institution_description


    def get_job(self, institutions, staff_institutions):
        job = {}
        to_process = [self.get_institution_id_ref(i) for i in institutions]
        for domain, i_true in staff_institutions.items():
            if domain != "Statistic":
                job[domain] = []
                for id_ref in i_true:
                    job[domain].append({
                        "institutionIDRef": id_ref,
                        "ProcessByDistributor": True if id_ref in to_process else False
                    })
            else:
                job["Statistic"] = {
                    "institutionIDRef": "#BFS",
                    "ProcessByDistributor": True if "#BFS" in to_process else False
                }
        if "#Tax" in to_process:
            job["Tax"] = {
                "ProcessByDistributor": True
            }
        return {
            "Addressees": [job]
        }

    def get_company_description(self, company_id):
        company_description = {
            "Name": {
                "HR-RC-Name": company_id.name
            }
        }

        if company_id.l10n_ch_uid:
            company_description["UID-BFS"] = {
                "UID": company_id.l10n_ch_uid
            }
        else:
            company_description["UID-BFS"] = {
                "Unknown": XSD_SKIP_VALUE
            }

        address = {
            "ZIP-Code": company_id.zip or missing_value,
            "City": company_id.city or missing_value
        }

        if company_id.street:
            address["Street"] = company_id.street
        if company_id.street2:
            address["ComplementaryLine"]: company_id.street2
        if company_id.l10n_ch_post_box:
            address["Postbox"] = company_id.l10n_ch_post_box
        if company_id.country_id:
            address["Country"] = company_id.country_id.name.upper()

        workplaces = []
        for workplace in company_id.l10n_ch_work_location_ids:
            workplace_description = dict()
            workplace_id_ref = self.get_workplace_id_ref(workplace)
            workplace_description["workplaceID"] = workplace_id_ref
            if workplace.bur_ree_number:
                workplace_description["BUR-REE-Number"] = workplace.bur_ree_number
            if workplace.in_house_id and not workplace.bur_ree_number:
                workplace_description["InHouseID"] = workplace.in_house_id
            address_extended = {
                "ComplementaryLine": workplace.partner_id.name,
                "ZIP-Code": workplace.partner_id.zip or missing_value,
                "City": workplace.partner_id.city or missing_value
            }
            if workplace.partner_id.street:
                address_extended["Street"] = workplace.partner_id.street
            if workplace.partner_id.country_id:
                address_extended["Country"] = workplace.partner_id.country_id.name.upper()
            if workplace.canton:
                address_extended["Canton"] = workplace.canton
            if workplace.municipality:
                address_extended["MunicipalityID"] = workplace.municipality

            workplaces.append({
                **workplace_description,
                "AddressExtended": address_extended,
                "CompanyWorkingTime": self.get_workplace_working_hours(workplace)
            })

        if company_id.l10n_ch_uses_delegate:
            delegate_desc = {
                "Name": {
                    "HR-RC-Name": company_id.l10n_ch_swissdec_delegate_name or missing_value,
                },
                "Address": {
                    "ZIP-Code": company_id.l10n_ch_delegate_zip or missing_value,
                    "City": company_id.l10n_ch_delegate_city or missing_value
                },
            }

            if company_id.l10n_ch_swissdec_delegate_ch_uid:
                delegate_desc["UID-BFS"] = company_id.l10n_ch_swissdec_delegate_ch_uid
            if company_id.l10n_ch_delegate_street:
                delegate_desc["Address"]["Street"] = company_id.l10n_ch_delegate_street
            if company_id.l10n_ch_delegate_street2:
                delegate_desc["Address"]["ComplementaryLine"] = company_id.l10n_ch_delegate_street2
            if company_id.l10n_ch_delegate_Po_Box:
                delegate_desc["Address"]["Postbox"] = company_id.l10n_ch_delegate_Po_Box
            if company_id.l10n_ch_delegate_country_id:
                delegate_desc["Address"]["Country"] = company_id.l10n_ch_delegate_country_id.name.upper()

            company_description["Delegate"] = delegate_desc

        return {
            "CompanyDescription": {
                **company_description,
                "Address": address,
                "Workplace": workplaces
            }
        }

    def _get_contact_person(self, company_id):
        contact_person = dict()
        if company_id.l10n_ch_contact_person_name and company_id.l10n_ch_contact_person_email and company_id.l10n_ch_contact_person_phone:
            contact_person["Name"] = company_id.l10n_ch_contact_person_name
            contact_person["EmailAddress"] = company_id.l10n_ch_contact_person_email
            contact_person["PhoneNumber"] = company_id.l10n_ch_contact_person_phone
            return {
                "ContactPerson": contact_person
            }
        else:
            return {}

    def create_declare_salary(self, institutions_to_process, company_id, staff, declaration_year, test_case=False, substitution_declaration_id=None, **kwargs):
        staff_institutions = {}
        if staff:
            for domain, institutions in staff.get("Institutions", {}).items():
                if isinstance(institutions, list):
                    staff_institutions[domain] = []
                    for institution in institutions:
                        staff_institutions[domain].append(institution.get("institutionID"))
                else:
                    staff_institutions[domain] = [institutions.get("institutionID")]
            job = {
                "Job": self.get_job(institutions_to_process, staff_institutions)
            }


            salary_declaration = {"SalaryDeclaration": {
                "schemaVersion": "3.0",
                "Company": {
                    **staff
                },
                "GeneralSalaryDeclarationDescription": {
                    "CreationDate": datetime.datetime.utcnow().isoformat() + 'Z',
                    "AccountingPeriod": [XSD_YMONTH, declaration_year, False],
                    **self._get_contact_person(company_id)
                },
            }}

            if substitution_declaration_id:
                declaration = {
                    **job,
                    "Substitution": {
                        "PredecessorDeclarationIDWithAcceptedState": substitution_declaration_id
                    },
                    **salary_declaration
                }
            else:
                declaration = {
                    **job,
                    **salary_declaration
                }

            return declaration
        else:
            return {}



    def create_get_status_from_declare_salary(self, job_key):
        return {
            "JobKey": job_key
        }

    def create_get_result_from_declare_salary(self, domain, key, password, institution_description):
        domain_data = {
            MAPPED_DOMAIN_IDENTIFICATION[domain]: {
                "Key": key,
                "Password": password,
            }
        }
        if institution_description:
            domain_data[MAPPED_DOMAIN_IDENTIFICATION[domain]]["Institution"] = institution_description

        return {
            "Domain": domain_data
        }

    def create_reply_dialog(self, domain, key, password, institution_description, dialog):
        domain_data = {
            MAPPED_DOMAIN_IDENTIFICATION[domain]: {
                "Key": key,
                "Password": password,
            }
        }
        if institution_description:
            domain_data[MAPPED_DOMAIN_IDENTIFICATION[domain]]["Institution"] = institution_description

        return {
            "Domain": domain_data,
            "DialogMessages": {
                "DialogMessage": [dialog]
            }
        }

    def create_poll_dialog(self, domain, key, password, institution_description, dialog_story_id):
        polling_dialog = {
            "Creation": fields.Datetime.now().isoformat(),
            "StoryID": str(uuid.uuid4().hex),
            "StandardDialogID": "0000.0002.0001-001",
            "Title": "Polling DialogMessage ELM",
            "Description": "Polling of a DialogMessage in ProcessingState",
            "Paragraph": [
                {
                    "ID": "100",
                    "Label": "StoryID of DialogMessage to poll",
                    "Value": {
                        "String": dialog_story_id
                    }
                }
            ]
        }

        domain_data = {
            MAPPED_DOMAIN_IDENTIFICATION[domain]: {
                "Key": key,
                "Password": password,
            }
        }
        if institution_description:
            domain_data[MAPPED_DOMAIN_IDENTIFICATION[domain]]["Institution"] = institution_description

        return {
            "Domain": domain_data,
            "DialogMessages": {
                "DialogMessage": [polling_dialog]
            }
        }
