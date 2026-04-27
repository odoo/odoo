# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestSwissdecCommon
from odoo.tests.common import tagged
from datetime import date
from collections import defaultdict


@tagged("post_install_l10n", "post_install", "-at_install", "swissdec_payroll")
class TestComputeWageIds(TestSwissdecCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Input Types
        cls.hourly_input_type = cls.env.ref(
            "l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours",
            raise_if_not_found=False,
        )
        cls.overtime_input_type = cls.env.ref(
            "l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours_100",
            raise_if_not_found=False,
        )
        cls.overtime_125_input_type = cls.env.ref(
            "l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours_125",
            raise_if_not_found=False,
        )
        cls.overtime_150_input_type = cls.env.ref(
            "l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours_150",
            raise_if_not_found=False,
        )
        cls.overtime_200_input_type = cls.env.ref(
            "l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours_200",
            raise_if_not_found=False,
        )
        cls.on_call_duty_125_input_type = cls.env.ref(
            "l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_on_call_125",
            raise_if_not_found=False,
        )
        cls.night_shift_110_input_type = cls.env.ref(
            "l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_night_110",
            raise_if_not_found=False,
        )
        cls.lesson_input_type = cls.env.ref(
            "l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons",
            raise_if_not_found=False,
        )

        # Leave Types
        cls.unpaid_leave_type = cls.env.ref(
            "l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_unpaid_lt",
            raise_if_not_found=False,
        )
        cls.illness_leave_type = cls.env.ref(
            "l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_illness_lt",
            raise_if_not_found=False,
        )
        cls.accident_leave_type = cls.env.ref(
            "l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_accident_lt",
            raise_if_not_found=False,
        )
        cls.maternity_leave_type = cls.env.ref(
            "l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_maternity_lt",
            raise_if_not_found=False,
        )
        cls.military_leave_type = cls.env.ref(
            "l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_military_lt",
            raise_if_not_found=False,
        )
        cls.interruption_work_leave_type = cls.env.ref(
            "l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_interruption_of_work_lt",
            raise_if_not_found=False,
        )

        cls.employee_monica = (
            cls.env["hr.employee"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "registration_number": "1",
                    "certificate": "higherVocEducation",
                    "name": "Monica Herz",
                    "resource_calendar_id": cls.env.ref("resource.resource_calendar_std").id,
                    "company_id": cls.muster_ag_company.id,
                    "country_id": cls.env.ref("base.ch").id,
                },
            )
        )

        cls.env["hr.contract"].create(
            {
                "l10n_ch_job_type": "lowerCadre",
                "name": "Contract For Monica Herz",
                "employee_id": cls.employee_monica.id,
                "resource_calendar_id": cls.env.ref("resource.resource_calendar_std").id,
                "company_id": cls.muster_ag_company.id,
                "structure_type_id": cls.env.ref(
                    "l10n_ch_hr_payroll.structure_type_employee_ch"
                ).id,
                "date_start": date(2022, 1, 1),
                "date_end": date(2023, 12, 31),
                "wage": 5000,
                "hourly_wage": 100,
                "wage_type": "monthly",
                "l10n_ch_lesson_wage": 50.0,
                "state": "open",
            }
        )

    def _validate_payslip_wage_ids(self, payslip, results):
        error = []
        wage_line_values = defaultdict(list)
        results_by_code = defaultdict(list)
        for w in payslip.l10n_ch_swiss_wage_ids:
            wage_line_values[w.code].append(w.amount)
        for code, value in results:
            results_by_code[code].append(value)
        for code, value_list in results_by_code.items():
            payslip_line_value = wage_line_values[code]
            if sorted(payslip_line_value) != sorted(value_list):
                error.append(
                    "Code: %s - Expected: %s - Reality: %s"
                    % (code, value_list, payslip_line_value)
                )
        for code in payslip.l10n_ch_swiss_wage_ids.mapped("code"):
            if not results_by_code[code]:
                error.append(
                    "Missing Line(s): '%s' - %s," % (code, wage_line_values[code])
                )
        if error:
            error.append("Payslip Actual Wage Values: ")
            error.append("        {")
            for wage in payslip.l10n_ch_swiss_wage_ids:
                error.append("            '%s': %s," % (wage.code, wage.amount))
            error.append("        }")
        self.assertEqual(len(error), 0, "\n" + "\n".join(error))

    def test_compute_wage_ids_1(self):
        contract = self.employee_monica.contract_id
        company = self.employee_monica.company_id
        self.env.company.l10n_ch_30_day_method = False

        monthly_wage_types = self.env["l10n.ch.hr.contract.wage"].create(
            [
                {
                    "amount": 8,
                    "input_type_id": self.overtime_input_type.id,
                    "contract_id": contract.id,
                    "uom": "hours",
                    "date_start": date(2023, 1, 1),
                },
                {
                    "amount": 7,
                    "input_type_id": self.overtime_125_input_type.id,
                    "contract_id": contract.id,
                    "uom": "hours",
                    "date_start": date(2023, 2, 1),
                },
                {
                    "amount": 12,
                    "input_type_id": self.overtime_150_input_type.id,
                    "contract_id": contract.id,
                    "uom": "hours",
                    "date_start": date(2023, 3, 1),
                },
                {
                    "amount": 11,
                    "input_type_id": self.night_shift_110_input_type.id,
                    "contract_id": contract.id,
                    "uom": "hours",
                },
                {
                    "amount": 17,
                    "input_type_id": self.on_call_duty_125_input_type.id,
                    "contract_id": contract.id,
                    "uom": "hours",
                    "date_start": date(2023, 4, 1),
                }
            ]
        )

        contract.update(
            {
                "l10n_ch_has_monthly": True,
                "l10n_ch_has_hourly": True,
                "l10n_ch_has_lesson": False,
                "l10n_ch_contract_wage_ids": monthly_wage_types.ids,
            }
        )
        self.env["hr.leave"].create(
            {
                "name": "Unpaid Time Off Jan",
                "employee_id": self.employee_monica.id,
                "holiday_status_id": self.unpaid_leave_type.id,
                "request_date_from": date(2023, 1, 1),
                "request_date_to": date(2023, 1, 5),
            }
        )
        self.env["hr.leave"].create(
            {
                "name": "Illness Time Off Jan - 01",
                "employee_id": self.employee_monica.id,
                "holiday_status_id": self.illness_leave_type.id,
                "request_date_from": date(2023, 1, 12),
                "request_date_to": date(2023, 1, 17),
            }
        )
        self.env["hr.leave"].create(
            {
                "name": "Illness Time Off Jan - 02",
                "employee_id": self.employee_monica.id,
                "holiday_status_id": self.illness_leave_type.id,
                "request_date_from": date(2023, 1, 18),
                "request_date_to": date(2023, 1, 21),
            }
        )
        self.env["hr.leave"].create(
            {
                "name": "Illness Time Off Feb",
                "employee_id": self.employee_monica.id,
                "holiday_status_id": self.illness_leave_type.id,
                "request_date_from": date(2023, 2, 10),
                "request_date_to": date(2023, 2, 21),
                "l10n_ch_continued_pay_percentage": 0.5,
                "l10n_ch_disability_percentage": 0.7,
            }
        )
        self.env["hr.leave"].create(
            {
                "name": "Accident Time Off Mar",
                "employee_id": self.employee_monica.id,
                "holiday_status_id": self.accident_leave_type.id,
                "request_date_from": date(2023, 3, 5),
                "request_date_to": date(2023, 3, 25),
            }
        )
        self.env["hr.leave"].create(
            {
                "name": "Interruption of work Time Off Apr",
                "employee_id": self.employee_monica.id,
                "holiday_status_id": self.interruption_work_leave_type.id,
                "request_date_from": date(2023, 4, 1),
                "request_date_to": date(2023, 4, 30),
            }
        )
        self.env["hr.leave"].create(
            {
                "name": "Maternity Time Off May",
                "employee_id": self.employee_monica.id,
                "holiday_status_id": self.maternity_leave_type.id,
                "request_date_from": date(2023, 5, 4),
                "request_date_to": date(2023, 5, 11),
            }
        )
        self.env["hr.leave"].create(
            {
                "name": "Military Time Off May",
                "employee_id": self.employee_monica.id,
                "holiday_status_id": self.maternity_leave_type.id,
                "request_date_from": date(2023, 5, 16),
                "request_date_to": date(2023, 5, 23),
            }
        )
        payslip_jan = self._l10n_ch_generate_swissdec_demo_payslip(
            contract, date(2023, 1, 1), date(2023, 1, 31), company.id
        )
        payslip_jan_results = [
            ("CH_UNPAID", 806.45),
            ("CH_ILLNESS_HOURLY", 0.0),
            ("CH_ILLNESS", 967.74),
            ("CH_ILLNESS_HOURLY", 0.0),
            ("CH_ILLNESS", 645.16),
            ("CH_1000", 2580.65),
            ("CH_1005", 0.0),
            ("CH_1065", 800.0),
            ("CH_1075", 1210.0),
        ]
        self._validate_payslip_wage_ids(payslip_jan, payslip_jan_results)

        payslip_feb = self._l10n_ch_generate_swissdec_demo_payslip(
            contract, date(2023, 2, 1), date(2023, 2, 28), company.id
        )
        payslip_feb_results = [
            ("CH_1000", 2857.14),
            ("CH_ILLNESS_HOURLY", 0.0),
            ("CH_1000", 642.86),
            ("CH_ILLNESS", 750.0),
            ("CH_1005", 0.0),
            ("CH_1061", 875.0),
            ("CH_1075", 1210.0),
        ]
        self._validate_payslip_wage_ids(payslip_feb, payslip_feb_results)

        payslip_mar = self._l10n_ch_generate_swissdec_demo_payslip(
            contract, date(2023, 3, 1), date(2023, 3, 31), company.id
        )
        payslip_mar_results = [
            ("CH_ACCIDENT_HOURLY", 0.0),
            ("CH_1000", 1612.9),
            ("CH_ACCIDENT", 3387.1),
            ("CH_1005", 0.0),
            ("CH_1066", 1800.0),
            ("CH_1075", 1210.0),
        ]
        self._validate_payslip_wage_ids(payslip_mar, payslip_mar_results)

        payslip_apr = self._l10n_ch_generate_swissdec_demo_payslip(
            contract, date(2023, 4, 1), date(2023, 4, 30), company.id
        )
        payslip_apr_results = [
            ('CH_Interruption', 0.0),
            ('CH_1000', 0.0),
            ('CH_1005', 0.0),
            ('CH_1071', 2125.0),
            ('CH_1075', 1210.0),
        ]
        self._validate_payslip_wage_ids(payslip_apr, payslip_apr_results)

        payslip_may = self._l10n_ch_generate_swissdec_demo_payslip(
            contract, date(2023, 5, 1), date(2023, 5, 31), company.id
        )
        payslip_may_results = [
            ('CH_MATERNITY_HOURLY', 0.0),
            ('CH_MATERNITY', 1290.32),
            ('CH_MATERNITY_HOURLY', 0.0),
            ('CH_MATERNITY', 1290.32),
            ('CH_1000', 2419.35),
            ('CH_1005', 0.0),
            ('CH_1075', 1210.0),
        ]
        self._validate_payslip_wage_ids(payslip_may, payslip_may_results)

    def test_compute_wage_ids_2(self):
        contract = self.employee_monica.contract_id
        company = self.employee_monica.company_id
        self.env.company.l10n_ch_30_day_method = True

        monthly_wage_types = self.env["l10n.ch.hr.contract.wage"].create(
            [
                {
                    "amount": 27,
                    "input_type_id": self.hourly_input_type.id,
                    "contract_id": contract.id,
                    "uom": "hours",
                },
                {
                    "amount": 3,
                    "input_type_id": self.lesson_input_type.id,
                    "contract_id": contract.id,
                    "uom": "hours",
                    "date_start": date(2023, 3, 1),
                },
                {
                    "amount": 5,
                    "input_type_id": self.lesson_input_type.id,
                    "contract_id": contract.id,
                    "uom": "hours",
                    "date_start": date(2023, 4, 1),
                },
            ]
        )

        contract.update(
            {
                "l10n_ch_has_monthly": True,
                "l10n_ch_has_hourly": True,
                "l10n_ch_has_lesson": True,
                "hourly_wage": 126,
                "l10n_ch_contract_wage_ids": monthly_wage_types.ids,
            }
        )

        self.env["hr.leave"].create(
            {
                "name": "Illness Time Off Mar",
                "employee_id": self.employee_monica.id,
                "holiday_status_id": self.illness_leave_type.id,
                "request_date_from": date(2023, 3, 10),
                "request_date_to": date(2023, 3, 21),
                "l10n_ch_continued_pay_percentage": 0.8,
                "l10n_ch_disability_percentage": 0.3,
            }
        )
        self.env["hr.leave"].create(
            {
                "name": "Unpaid Time Off Apr",
                "employee_id": self.employee_monica.id,
                "holiday_status_id": self.unpaid_leave_type.id,
                "request_date_from": date(2023, 4, 4),
                "request_date_to": date(2023, 4, 13),
            }
        )
        payslip_mar = self._l10n_ch_generate_swissdec_demo_payslip(
            contract, date(2023, 3, 1), date(2023, 3, 31), company.id
        )
        payslip_mar_results = [
            ('CH_1000', 1400.0),
            ('CH_ILLNESS_HOURLY', 0.0),
            ('CH_ILLNESS', 480.0),
            ('CH_1000', 3000.0),
            ('CH_1005', 3402.0),
            ('CH_1006', 150.0),
        ]
        self._validate_payslip_wage_ids(payslip_mar, payslip_mar_results)

        payslip_apr = self._l10n_ch_generate_swissdec_demo_payslip(
            contract, date(2023, 4, 1), date(2023, 4, 30), company.id
        )
        payslip_apr_results = [
            ('CH_UNPAID', 1666.67),
            ('CH_1000', 3333.33),
            ('CH_1005', 3402.0),
            ('CH_1006', 250.0),
        ]
        self._validate_payslip_wage_ids(payslip_apr, payslip_apr_results)

    def test_compute_wage_ids_3(self):
        contract = self.employee_monica.contract_id
        company = self.employee_monica.company_id
        self.env.company.l10n_ch_30_day_method = False

        monthly_wage_types = self.env["l10n.ch.hr.contract.wage"].create(
            [
                {
                    "amount": 10,
                    "input_type_id": self.overtime_200_input_type.id,
                    "contract_id": contract.id,
                    "uom": "hours",
                    "date_start": date(2023, 6, 1),
                },
            ]
        )

        contract.update(
            {
                "l10n_ch_has_monthly": False,
                "l10n_ch_has_hourly": True,
                "l10n_ch_has_lesson": False,
                "l10n_ch_contract_wage_ids": monthly_wage_types.ids,
            }
        )

        payslip_jun = self._l10n_ch_generate_swissdec_demo_payslip(
            contract, date(2023, 6, 1), date(2023, 6, 30), company.id
        )
        payslip_jun_results = [
            ("CH_1005", 0),
            ("CH_1068", 2000.0),
        ]
        self._validate_payslip_wage_ids(payslip_jun, payslip_jun_results)
