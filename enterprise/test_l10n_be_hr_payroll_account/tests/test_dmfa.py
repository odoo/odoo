# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from datetime import date, datetime
from freezegun import freeze_time
from unittest.mock import patch, MagicMock

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_be_hr_payroll.models.certificate import Certificate
from odoo.addons.l10n_be_hr_payroll_dmfa_sftp.models.utils import xml_str_to_dict
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'dmfa')
@patch.object(Certificate, '_decode_certificate_for_be_dmfa_xml', lambda contract, xml_str: b'dummy\r\nsignature\r\n')
class TestDMFA(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('be')
    def setUpClass(cls):
        super().setUpClass()

        cls.payroll_manager = mail_new_test_user(cls.env, login='blou', groups='hr_payroll.group_hr_payroll_manager,fleet.fleet_group_manager')

        cls.belgian_company = cls.company_data['company']

        cls.belgian_company.write({
            'vat': 'BE0897223670',
            'phone': '0471098765',
            'street': 'Test street',
            'city': 'Test city',
            'zip': '8292',
            'l10n_be_company_number': '0123456789',
            'l10n_be_revenue_code': '1234',
            'dmfa_employer_class': '010',
            'onss_registration_number': '123456789',
            'onss_company_id': '0123456789',
            'onss_expeditor_number': '123456',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.calendar_38h = cls.env['resource.calendar'].create({
            'name': 'Standard 38 hours/week',
            'tz': 'Europe/Brussels',
            'company_id': cls.belgian_company.id,
            'hours_per_day': 7.6,
            'attendance_ids': [(5, 0, 0),
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'})
            ],
        })

        cls.calendar_4_5_wednesday_off = cls.env['resource.calendar'].create([{
            'name': "Test Calendar: 4/5 Wednesday Off",
            'company_id': cls.belgian_company.id,
            'hours_per_day': 7.6,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': False,
            'hours_per_week': 38.0,
            'full_time_required_hours': 38.0,
            'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                'name': "Attendance",
                'dayofweek': dayofweek,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'day_period': day_period,
                'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id,
            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 8.0, 12.0, "morning"),
                ("0", 12.0, 13.0, "lunch"),
                ("0", 13.0, 16.6, "afternoon"),
                ("1", 8.0, 12.0, "morning"),
                ("1", 12.0, 13.0, "lunch"),
                ("1", 13.0, 16.6, "afternoon"),
                ("3", 8.0, 12.0, "morning"),
                ("3", 12.0, 13.0, "lunch"),
                ("3", 13.0, 16.6, "afternoon"),
                ("4", 8.0, 12.0, "morning"),
                ("4", 12.0, 13.0, "lunch"),
                ("4", 13.0, 16.6, "afternoon"),
            ]],
        }])

        cls.calendar_0_hours_per_week = cls.env['resource.calendar'].create([{
            'name': "Test Calendar: 0 Hours per week",
            'company_id': cls.belgian_company.id,
            'hours_per_day': 0,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': False,
            'hours_per_week': 0,
            'full_time_required_hours': 38,
            'attendance_ids': [(5, 0, 0)],
        }])

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Laurie Poiret',
            'niss': '91111111192',
            'marital': 'single',
            'private_street': '58 rue des Wallons',
            'private_city': 'Louvain-la-Neuve',
            'private_zip': '1348',
            'private_country_id': cls.env.ref("base.be").id,
            'private_phone': '+0032476543210',
            'private_email': 'laurie.poiret@example.com',
            'resource_calendar_id': cls.calendar_38h.id,
            'company_id': cls.belgian_company.id,
        })

        cls.brand = cls.env['fleet.vehicle.model.brand'].create({
            'name': "Test Brand"
        })

        cls.model = cls.env['fleet.vehicle.model'].create({
            'name': "Test Model",
            'brand_id': cls.brand.id
        })

        cls.car = cls.env['fleet.vehicle'].create({
            'name': "Test Car",
            'license_plate': "TEST",
            'driver_id': cls.employee.work_contact_id.id,
            'company_id': cls.belgian_company.id,
            'model_id': cls.model.id,
            'first_contract_date': date(2020, 10, 8),
            'co2': 88.0,
            'car_value': 38000.0,
            'fuel_type': "diesel",
            'acquisition_date': date(2020, 1, 1)
        })

        cls.vehicle_contract = cls.env['fleet.vehicle.log.contract'].create({
            'name': "Test Contract",
            'vehicle_id': cls.car.id,
            'company_id': cls.belgian_company.id,
            'start_date': date(2020, 10, 8),
            'expiration_date': date(2021, 10, 8),
            'state': "open",
            'cost_generated': 0.0,
            'cost_frequency': "monthly",
            'recurring_cost_amount_depreciated': 450.0
        })

        cls.contract = cls.env['hr.contract'].create({
            'name': "Contract For Payslip Test",
            'employee_id': cls.employee.id,
            'resource_calendar_id': cls.calendar_38h.id,
            'company_id': cls.belgian_company.id,
            'date_generated_from': datetime(2020, 9, 1, 0, 0, 0),
            'date_generated_to': datetime(2020, 9, 1, 0, 0, 0),
            'car_id': cls.car.id,
            'structure_type_id': cls.env.ref('hr_contract.structure_type_employee_cp200').id,
            'date_start': date(2018, 12, 31),
            'wage': 3000,
            'wage_on_signature': 3000,
            'state': "open",
            'transport_mode_car': True,
            'fuel_card': 150.0,
            'internet': 38.0,
            'representation_fees': 300.0,
            'mobile': 30.0,
            'meal_voucher_amount': 7.45,
            'eco_checks': 250.0,
        })

        company = cls.employee.company_id
        cls.payroll_manager.company_ids = [(4, company.id)]
        cls.employee.address_id = cls.employee.company_id.partner_id
        cls.env['l10n_be.dmfa.location.unit'].with_user(cls.payroll_manager).create({
            'company_id': cls.employee.company_id.id,
            'code': 123,
            'partner_id': cls.employee.address_id.id,
        })

    def _generate_dmfa_declaration(self, file_type='S', return_declaration=False, skip_signature=True):
        dmfa = self.env['l10n_be.dmfa'].with_user(self.payroll_manager).create({
            'reference': 'TESTDMFA',
            'company_id': self.belgian_company.id,
            'year': '2025',
            'quarter': '1',
            'declaration_type': 'batch',
            'file_type': file_type,
        })
        with patch('time.strftime', return_value='10:00:00.000'):
            dmfa.with_context(dmfa_skip_signature=skip_signature).generate_dmfa_xml_report()
        self.assertFalse(dmfa.error_message)
        self.assertEqual(dmfa.validation_state, 'done')
        if return_declaration:
            return dmfa
        dmfa_dict = xml_str_to_dict(base64.b64decode(dmfa.dmfa_xml))
        return dmfa_dict

    @freeze_time("2025-04-10 10:00:00")
    def test_01_empty_dmfa(self):
        dmfa_dict = self._generate_dmfa_declaration()
        expected_dict = {'DmfAOriginal': {'@{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation': 'DmfAOriginal_20211.xsd', 'Form': {'Identification': 'DMFA', 'FormCreationDate': '2025-04-10', 'FormCreationHour': '10:00:00.000', 'AttestationStatus': '0', 'TypeForm': 'SU', 'Reference': {'ReferenceType': '1', 'ReferenceOrigin': '1', 'ReferenceNbr': 'TESTDMFA'}, 'EmployerDeclaration': {'Quarter': '20251', 'NOSSRegistrationNbr': '123456789', 'Trusteeship': '0', 'CompanyID': '0123456789', 'NetOwedAmount': '00000000000', 'System5': '0', 'ContributionUnrelatedToNP': [{'UnrelatedEmployerClass': '010', 'UnrelatedWorkerCode': '862', 'UnrelatedAmount': '00000000000'}, {'UnrelatedEmployerClass': '010', 'UnrelatedWorkerCode': '870', 'UnrelatedCalculationBasis': '00000000000', 'UnrelatedAmount': '00000000000'}]}}}}
        self.assertDictEqual(dmfa_dict, expected_dict)

    @freeze_time("2025-04-10 10:00:00")
    def test_02_declaration_classic_employee_with_commissions(self):
        payslips = self.env['hr.payslip'].create([{
            'name': 'Payslip Jan 2025 %s',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 1, 1),
            'date_to': datetime(2025, 1, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 2000,
            })],
        }, {
            'name': 'Payslip Feb 2025',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 2, 1),
            'date_to': datetime(2025, 2, 28),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
        }, {
            'name': 'Payslip Mar 2025',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 3, 1),
            'date_to': datetime(2025, 3, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
        }])
        payslips.compute_sheet()
        payslips.action_payslip_done()
        dmfa_dict = self._generate_dmfa_declaration()
        expected_dict = {'DmfAOriginal': {'@{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation': 'DmfAOriginal_20211.xsd', 'Form': {'Identification': 'DMFA', 'FormCreationDate': '2025-04-10', 'FormCreationHour': '10:00:00.000', 'AttestationStatus': '0', 'TypeForm': 'SU', 'Reference': {'ReferenceType': '1', 'ReferenceOrigin': '1', 'ReferenceNbr': 'TESTDMFA'}, 'EmployerDeclaration': {'Quarter': '20251', 'NOSSRegistrationNbr': '123456789', 'Trusteeship': '0', 'CompanyID': '0123456789', 'NetOwedAmount': '00000430542', 'System5': '0', 'NaturalPerson': {'NaturalPersonSequenceNbr': '1', 'INSS': '91111111192', 'NaturalPersonUserReference': str(self.employee.id), 'WorkerRecord': {'EmployerClass': '010', 'WorkerCode': '495', 'NOSSQuarterStartingDate': '2025-01-01', 'NOSSQuarterEndingDate': '2025-03-31', 'Border': '0', 'Occupation': {'OccupationSequenceNbr': '1', 'OccupationStartingDate': '2018-12-31', 'JointCommissionNbr': '200', 'WorkingDaysSystem': '500', 'ContractType': '0', 'RefMeanWorkingHours': '3800', 'MeanWorkingHours': '3800', 'Retired': '0', 'OccupationUserReference': str(self.contract.id), 'LocalUnitID': '0000000123', 'Service': {'ServiceSequenceNbr': '1', 'ServiceCode': '001', 'ServiceNbrDays': '06400', 'ServiceNbrHours': '48640'}, 'Remun': [{'RemunSequenceNbr': '1', 'RemunCode': '001', 'RemunAmount': '00000902700'}, {'RemunSequenceNbr': '2', 'RemunCode': '010', 'RemunAmount': '00000047880'}, {'RemunSequenceNbr': '3', 'RemunCode': '002', 'BonusPaymentFrequency': '00', 'RemunAmount': '00000200000'}], 'OccupationDeduction': {'DeductionCode': '3000', 'DeductionAmount': '00000000000'}}, 'WorkerContribution': [{'ContributionWorkerCode': '256', 'ContributionType': '0', 'ContributionCalculationBasis': '00001102700', 'ContributionAmount': '00000000110'}, {'ContributionWorkerCode': '255', 'ContributionType': '0', 'ContributionCalculationBasis': '00001102700', 'ContributionAmount': '00000000221'}, {'ContributionWorkerCode': '495', 'ContributionType': '0', 'ContributionCalculationBasis': '00001102700', 'ContributionAmount': '00000419798'}, {'ContributionWorkerCode': '809', 'ContributionType': '5', 'ContributionCalculationBasis': '00001102700', 'ContributionAmount': '00000001985'}, {'ContributionWorkerCode': '810', 'ContributionType': '0', 'ContributionCalculationBasis': '00001102700', 'ContributionAmount': '00000001875'}, {'ContributionWorkerCode': '831', 'ContributionType': '0', 'ContributionCalculationBasis': '00001102700', 'ContributionAmount': '00000002536'}, {'ContributionWorkerCode': '856', 'ContributionType': '0', 'ContributionAmount': '00000005772'}, {'ContributionWorkerCode': '859', 'ContributionType': '0', 'ContributionCalculationBasis': '00001102700', 'ContributionAmount': '00000001103'}], 'WorkerDeduction': {'DeductionCode': '0001', 'DeductionAmount': '00000012824'}}}, 'CompanyVehicle': {'CompanyVehicleSequenceNbr': '1', 'LicensePlate': 'TEST'}, 'ContributionUnrelatedToNP': [{'UnrelatedEmployerClass': '010', 'UnrelatedWorkerCode': '862', 'UnrelatedAmount': '00000009966'}, {'UnrelatedEmployerClass': '010', 'UnrelatedWorkerCode': '870', 'UnrelatedCalculationBasis': '00000000000', 'UnrelatedAmount': '00000000000'}]}}}}
        self.assertDictEqual(dmfa_dict, expected_dict)

    @freeze_time("2025-04-10 10:00:00")
    def test_03_declaration_employee_partial_credit_time(self):
        self.contract.date_end = date(2025, 2, 28)
        contract_credit_time = self.env['hr.contract'].create({
            'name': "Contract Credit Time",
            'employee_id': self.employee.id,
            'resource_calendar_id': self.calendar_4_5_wednesday_off.id,
            'standard_calendar_id': self.calendar_38h.id,
            'time_credit': True,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
            'company_id': self.belgian_company.id,
            'date_generated_from': datetime(2020, 9, 1, 0, 0, 0),
            'date_generated_to': datetime(2020, 9, 1, 0, 0, 0),
            'car_id': self.car.id,
            'structure_type_id': self.env.ref('hr_contract.structure_type_employee_cp200').id,
            'date_start': date(2025, 3, 1),
            'wage': 3000 * 4 / 5,
            'wage_on_signature': 3000 * 4 / 5,
            'state': "open",
            'transport_mode_car': True,
            'fuel_card': 150.0,
            'internet': 38.0,
            'representation_fees': 300.0,
            'mobile': 30.0,
            'meal_voucher_amount': 7.45,
            'eco_checks': 250.0,
        })
        payslips = self.env['hr.payslip'].create([{
            'name': 'Payslip Jan 2025 %s',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 1, 1),
            'date_to': datetime(2025, 1, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 2000,
            })],
        }, {
            'name': 'Payslip Feb 2025',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 2, 1),
            'date_to': datetime(2025, 2, 28),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
        }, {
            'name': 'Payslip Mar 2025',
            'contract_id': contract_credit_time.id,
            'date_from': datetime(2025, 3, 1),
            'date_to': datetime(2025, 3, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
        }])
        payslips.compute_sheet()
        payslips.action_payslip_done()
        dmfa_dict = self._generate_dmfa_declaration()
        expected_dict = {'DmfAOriginal': {'@{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation': 'DmfAOriginal_20211.xsd', 'Form': {'Identification': 'DMFA', 'FormCreationDate': '2025-04-10', 'FormCreationHour': '10:00:00.000', 'AttestationStatus': '0', 'TypeForm': 'SU', 'Reference': {'ReferenceType': '1', 'ReferenceOrigin': '1', 'ReferenceNbr': 'TESTDMFA'}, 'EmployerDeclaration': {'Quarter': '20251', 'NOSSRegistrationNbr': '123456789', 'Trusteeship': '0', 'CompanyID': '0123456789', 'NetOwedAmount': '00000383848', 'System5': '0', 'NaturalPerson': {'NaturalPersonSequenceNbr': '1', 'INSS': '91111111192', 'NaturalPersonUserReference': str(self.employee.id), 'WorkerRecord': {'EmployerClass': '010', 'WorkerCode': '495', 'NOSSQuarterStartingDate': '2025-01-01', 'NOSSQuarterEndingDate': '2025-03-31', 'Border': '0', 'Occupation': [{'OccupationSequenceNbr': '1', 'OccupationStartingDate': '2025-03-01', 'JointCommissionNbr': '200', 'WorkingDaysSystem': '400', 'ContractType': '0', 'RefMeanWorkingHours': '3800', 'MeanWorkingHours': '3040', 'ReorganisationMeasure': '4', 'Retired': '0', 'OccupationUserReference': str(contract_credit_time.id), 'LocalUnitID': '0000000123', 'Service': {'ServiceSequenceNbr': '1', 'ServiceCode': '001', 'ServiceNbrDays': '01700', 'ServiceNbrHours': '12920'}, 'Remun': [{'RemunSequenceNbr': '1', 'RemunCode': '001', 'RemunAmount': '00000240900'}, {'RemunSequenceNbr': '2', 'RemunCode': '010', 'RemunAmount': '00000015960'}], 'OccupationDeduction': {'DeductionCode': '3000', 'DeductionAmount': '00000007166'}}, {'OccupationSequenceNbr': '2', 'OccupationStartingDate': '2018-12-31', 'OccupationEndingDate': '2025-02-28', 'JointCommissionNbr': '200', 'WorkingDaysSystem': '500', 'ContractType': '0', 'RefMeanWorkingHours': '3800', 'MeanWorkingHours': '3800', 'Retired': '0', 'OccupationUserReference': str(self.contract.id), 'LocalUnitID': '0000000123', 'Service': {'ServiceSequenceNbr': '1', 'ServiceCode': '001', 'ServiceNbrDays': '04300', 'ServiceNbrHours': '32680'}, 'Remun': [{'RemunSequenceNbr': '1', 'RemunCode': '001', 'RemunAmount': '00000601800'}, {'RemunSequenceNbr': '2', 'RemunCode': '010', 'RemunAmount': '00000031920'}, {'RemunSequenceNbr': '3', 'RemunCode': '002', 'BonusPaymentFrequency': '00', 'RemunAmount': '00000200000'}], 'OccupationDeduction': {'DeductionCode': '3000', 'DeductionAmount': '00000000000'}}], 'WorkerContribution': [{'ContributionWorkerCode': '256', 'ContributionType': '0', 'ContributionCalculationBasis': '00001042700', 'ContributionAmount': '00000000104'}, {'ContributionWorkerCode': '255', 'ContributionType': '0', 'ContributionCalculationBasis': '00001042700', 'ContributionAmount': '00000000209'}, {'ContributionWorkerCode': '495', 'ContributionType': '0', 'ContributionCalculationBasis': '00001042700', 'ContributionAmount': '00000396956'}, {'ContributionWorkerCode': '809', 'ContributionType': '5', 'ContributionCalculationBasis': '00001042700', 'ContributionAmount': '00000001877'}, {'ContributionWorkerCode': '810', 'ContributionType': '0', 'ContributionCalculationBasis': '00001042700', 'ContributionAmount': '00000001773'}, {'ContributionWorkerCode': '831', 'ContributionType': '0', 'ContributionCalculationBasis': '00001042700', 'ContributionAmount': '00000002398'}, {'ContributionWorkerCode': '856', 'ContributionType': '0', 'ContributionAmount': '00000005112'}, {'ContributionWorkerCode': '859', 'ContributionType': '0', 'ContributionCalculationBasis': '00001042700', 'ContributionAmount': '00000001043'}], 'WorkerDeduction': {'DeductionCode': '0001', 'DeductionAmount': '00000028424'}}}, 'CompanyVehicle': {'CompanyVehicleSequenceNbr': '1', 'LicensePlate': 'TEST'}, 'ContributionUnrelatedToNP': [{'UnrelatedEmployerClass': '010', 'UnrelatedWorkerCode': '862', 'UnrelatedAmount': '00000009966'}, {'UnrelatedEmployerClass': '010', 'UnrelatedWorkerCode': '870', 'UnrelatedCalculationBasis': '00000000000', 'UnrelatedAmount': '00000000000'}]}}}}
        self.assertDictEqual(dmfa_dict, expected_dict)

    @freeze_time("2025-04-10 10:00:00")
    def test_04_declaration_employee_full_credit_time(self):
        self.contract.date_end = date(2025, 2, 28)
        contract_credit_time = self.env['hr.contract'].create({
            'name': "Contract Credit Time",
            'employee_id': self.employee.id,
            'resource_calendar_id': self.calendar_0_hours_per_week.id,
            'standard_calendar_id': self.calendar_38h.id,
            'time_credit': True,
            'work_time_rate': 0,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
            'company_id': self.belgian_company.id,
            'date_generated_from': datetime(2020, 9, 1, 0, 0, 0),
            'date_generated_to': datetime(2020, 9, 1, 0, 0, 0),
            'car_id': self.car.id,
            'structure_type_id': self.env.ref('hr_contract.structure_type_employee_cp200').id,
            'date_start': date(2025, 3, 1),
            'wage': 3000 * 4 / 5,
            'wage_on_signature': 3000 * 4 / 5,
            'state': "open",
            'transport_mode_car': True,
            'fuel_card': 150.0,
            'internet': 38.0,
            'representation_fees': 300.0,
            'mobile': 30.0,
            'meal_voucher_amount': 7.45,
            'eco_checks': 250.0,
        })
        payslips = self.env['hr.payslip'].create([{
            'name': 'Payslip Jan 2025 %s',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 1, 1),
            'date_to': datetime(2025, 1, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 2000,
            })],
        }, {
            'name': 'Payslip Feb 2025',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 2, 1),
            'date_to': datetime(2025, 2, 28),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
        }, {
            'name': 'Payslip Mar 2025',
            'contract_id': contract_credit_time.id,
            'date_from': datetime(2025, 3, 1),
            'date_to': datetime(2025, 3, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
        }])
        payslips.compute_sheet()
        payslips.action_payslip_done()
        dmfa_dict = self._generate_dmfa_declaration()
        expected_dict = {'DmfAOriginal': {'@{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation': 'DmfAOriginal_20211.xsd', 'Form': {'Identification': 'DMFA', 'FormCreationDate': '2025-04-10', 'FormCreationHour': '10:00:00.000', 'AttestationStatus': '0', 'TypeForm': 'SU', 'Reference': {'ReferenceType': '1', 'ReferenceOrigin': '1', 'ReferenceNbr': 'TESTDMFA'}, 'EmployerDeclaration': {'Quarter': '20251', 'NOSSRegistrationNbr': '123456789', 'Trusteeship': '0', 'CompanyID': '0123456789', 'NetOwedAmount': '00000318339', 'System5': '0', 'NaturalPerson': {'NaturalPersonSequenceNbr': '1', 'INSS': '91111111192', 'NaturalPersonUserReference': str(self.employee.id), 'WorkerRecord': {'EmployerClass': '010', 'WorkerCode': '495', 'NOSSQuarterStartingDate': '2025-01-01', 'NOSSQuarterEndingDate': '2025-03-31', 'Border': '0', 'Occupation': [{'OccupationSequenceNbr': '1', 'OccupationStartingDate': '2025-03-01', 'JointCommissionNbr': '200', 'WorkingDaysSystem': '000', 'ContractType': '0', 'RefMeanWorkingHours': '3800', 'MeanWorkingHours': '0000', 'ReorganisationMeasure': '3', 'Retired': '0', 'OccupationUserReference': str(contract_credit_time.id), 'LocalUnitID': '0000000123'}, {'OccupationSequenceNbr': '2', 'OccupationStartingDate': '2018-12-31', 'OccupationEndingDate': '2025-02-28', 'JointCommissionNbr': '200', 'WorkingDaysSystem': '500', 'ContractType': '0', 'RefMeanWorkingHours': '3800', 'MeanWorkingHours': '3800', 'Retired': '0', 'OccupationUserReference': str(self.contract.id), 'LocalUnitID': '0000000123', 'Service': {'ServiceSequenceNbr': '1', 'ServiceCode': '001', 'ServiceNbrDays': '04300', 'ServiceNbrHours': '32680'}, 'Remun': [{'RemunSequenceNbr': '1', 'RemunCode': '001', 'RemunAmount': '00000601800'}, {'RemunSequenceNbr': '2', 'RemunCode': '010', 'RemunAmount': '00000031920'}, {'RemunSequenceNbr': '3', 'RemunCode': '002', 'BonusPaymentFrequency': '00', 'RemunAmount': '00000200000'}], 'OccupationDeduction': {'DeductionCode': '3000', 'DeductionAmount': '00000000000'}}], 'WorkerContribution': [{'ContributionWorkerCode': '256', 'ContributionType': '0', 'ContributionCalculationBasis': '00000801800', 'ContributionAmount': '00000000080'}, {'ContributionWorkerCode': '255', 'ContributionType': '0', 'ContributionCalculationBasis': '00000801800', 'ContributionAmount': '00000000160'}, {'ContributionWorkerCode': '495', 'ContributionType': '0', 'ContributionCalculationBasis': '00000801800', 'ContributionAmount': '00000305245'}, {'ContributionWorkerCode': '809', 'ContributionType': '5', 'ContributionCalculationBasis': '00000801800', 'ContributionAmount': '00000001443'}, {'ContributionWorkerCode': '810', 'ContributionType': '0', 'ContributionCalculationBasis': '00000801800', 'ContributionAmount': '00000001363'}, {'ContributionWorkerCode': '831', 'ContributionType': '0', 'ContributionCalculationBasis': '00000801800', 'ContributionAmount': '00000001844'}, {'ContributionWorkerCode': '856', 'ContributionType': '0', 'ContributionAmount': '00000003848'}, {'ContributionWorkerCode': '859', 'ContributionType': '0', 'ContributionCalculationBasis': '00000801800', 'ContributionAmount': '00000000802'}], 'WorkerDeduction': {'DeductionCode': '0001', 'DeductionAmount': '00000006412'}}}, 'CompanyVehicle': {'CompanyVehicleSequenceNbr': '1', 'LicensePlate': 'TEST'}, 'ContributionUnrelatedToNP': [{'UnrelatedEmployerClass': '010', 'UnrelatedWorkerCode': '862', 'UnrelatedAmount': '00000009966'}, {'UnrelatedEmployerClass': '010', 'UnrelatedWorkerCode': '870', 'UnrelatedCalculationBasis': '00000000000', 'UnrelatedAmount': '00000000000'}]}}}}
        self.assertDictEqual(dmfa_dict, expected_dict)

    @freeze_time("2025-04-10 10:00:00")
    def test_05_declaration_employee_partial_incapacity(self):
        self.contract.date_end = date(2025, 2, 28)
        contract_credit_time = self.env['hr.contract'].create({
            'name': "Contract Credit Time",
            'employee_id': self.employee.id,
            'resource_calendar_id': self.calendar_0_hours_per_week.id,
            'standard_calendar_id': self.calendar_38h.id,
            'time_credit': True,
            'work_time_rate': 0,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_partial_incapacity').id,
            'company_id': self.belgian_company.id,
            'date_generated_from': datetime(2020, 9, 1, 0, 0, 0),
            'date_generated_to': datetime(2020, 9, 1, 0, 0, 0),
            'car_id': self.car.id,
            'structure_type_id': self.env.ref('hr_contract.structure_type_employee_cp200').id,
            'date_start': date(2025, 3, 1),
            'wage': 3000 * 4 / 5,
            'wage_on_signature': 3000 * 4 / 5,
            'state': "open",
            'transport_mode_car': True,
            'fuel_card': 150.0,
            'internet': 38.0,
            'representation_fees': 300.0,
            'mobile': 30.0,
            'meal_voucher_amount': 7.45,
            'eco_checks': 250.0,
        })
        payslips = self.env['hr.payslip'].create([{
            'name': 'Payslip Jan 2025 %s',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 1, 1),
            'date_to': datetime(2025, 1, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 2000,
            })],
        }, {
            'name': 'Payslip Feb 2025',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 2, 1),
            'date_to': datetime(2025, 2, 28),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
        }, {
            'name': 'Payslip Mar 2025',
            'contract_id': contract_credit_time.id,
            'date_from': datetime(2025, 3, 1),
            'date_to': datetime(2025, 3, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
        }])
        payslips.compute_sheet()
        payslips.action_payslip_done()
        dmfa_dict = self._generate_dmfa_declaration()
        expected_dict = {'DmfAOriginal': {'@{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation': 'DmfAOriginal_20211.xsd', 'Form': {'Identification': 'DMFA', 'FormCreationDate': '2025-04-10', 'FormCreationHour': '10:00:00.000', 'AttestationStatus': '0', 'TypeForm': 'SU', 'Reference': {'ReferenceType': '1', 'ReferenceOrigin': '1', 'ReferenceNbr': 'TESTDMFA'}, 'EmployerDeclaration': {'Quarter': '20251', 'NOSSRegistrationNbr': '123456789', 'Trusteeship': '0', 'CompanyID': '0123456789', 'NetOwedAmount': '00000318339', 'System5': '0', 'NaturalPerson': {'NaturalPersonSequenceNbr': '1', 'INSS': '91111111192', 'NaturalPersonUserReference': str(self.employee.id), 'WorkerRecord': {'EmployerClass': '010', 'WorkerCode': '495', 'NOSSQuarterStartingDate': '2025-01-01', 'NOSSQuarterEndingDate': '2025-03-31', 'Border': '0', 'Occupation': [{'OccupationSequenceNbr': '1', 'OccupationStartingDate': '2025-03-01', 'JointCommissionNbr': '200', 'WorkingDaysSystem': '500', 'ContractType': '0', 'RefMeanWorkingHours': '3800', 'MeanWorkingHours': '3800', 'ReorganisationMeasure': '5', 'Retired': '0', 'OccupationUserReference': str(contract_credit_time.id), 'LocalUnitID': '0000000123', 'Service': {'ServiceSequenceNbr': '1', 'ServiceCode': '050', 'ServiceNbrDays': '02100', 'ServiceNbrHours': '15960'}}, {'OccupationSequenceNbr': '2', 'OccupationStartingDate': '2018-12-31', 'OccupationEndingDate': '2025-02-28', 'JointCommissionNbr': '200', 'WorkingDaysSystem': '500', 'ContractType': '0', 'RefMeanWorkingHours': '3800', 'MeanWorkingHours': '3800', 'Retired': '0', 'OccupationUserReference': str(self.contract.id), 'LocalUnitID': '0000000123', 'Service': {'ServiceSequenceNbr': '1', 'ServiceCode': '001', 'ServiceNbrDays': '04300', 'ServiceNbrHours': '32680'}, 'Remun': [{'RemunSequenceNbr': '1', 'RemunCode': '001', 'RemunAmount': '00000601800'}, {'RemunSequenceNbr': '2', 'RemunCode': '010', 'RemunAmount': '00000031920'}, {'RemunSequenceNbr': '3', 'RemunCode': '002', 'BonusPaymentFrequency': '00', 'RemunAmount': '00000200000'}], 'OccupationDeduction': {'DeductionCode': '3000', 'DeductionAmount': '00000000000'}}], 'WorkerContribution': [{'ContributionWorkerCode': '256', 'ContributionType': '0', 'ContributionCalculationBasis': '00000801800', 'ContributionAmount': '00000000080'}, {'ContributionWorkerCode': '255', 'ContributionType': '0', 'ContributionCalculationBasis': '00000801800', 'ContributionAmount': '00000000160'}, {'ContributionWorkerCode': '495', 'ContributionType': '0', 'ContributionCalculationBasis': '00000801800', 'ContributionAmount': '00000305245'}, {'ContributionWorkerCode': '809', 'ContributionType': '5', 'ContributionCalculationBasis': '00000801800', 'ContributionAmount': '00000001443'}, {'ContributionWorkerCode': '810', 'ContributionType': '0', 'ContributionCalculationBasis': '00000801800', 'ContributionAmount': '00000001363'}, {'ContributionWorkerCode': '831', 'ContributionType': '0', 'ContributionCalculationBasis': '00000801800', 'ContributionAmount': '00000001844'}, {'ContributionWorkerCode': '856', 'ContributionType': '0', 'ContributionAmount': '00000003848'}, {'ContributionWorkerCode': '859', 'ContributionType': '0', 'ContributionCalculationBasis': '00000801800', 'ContributionAmount': '00000000802'}], 'WorkerDeduction': {'DeductionCode': '0001', 'DeductionAmount': '00000006412'}}}, 'CompanyVehicle': {'CompanyVehicleSequenceNbr': '1', 'LicensePlate': 'TEST'}, 'ContributionUnrelatedToNP': [{'UnrelatedEmployerClass': '010', 'UnrelatedWorkerCode': '862', 'UnrelatedAmount': '00000009966'}, {'UnrelatedEmployerClass': '010', 'UnrelatedWorkerCode': '870', 'UnrelatedCalculationBasis': '00000000000', 'UnrelatedAmount': '00000000000'}]}}}}
        self.assertDictEqual(dmfa_dict, expected_dict)

    @freeze_time("2025-04-10 10:00:00")
    def test_06_declaration_employee_no_notice_period(self):
        departure_notice = self.env['hr.payslip.employee.depature.notice'].create({
            'employee_id': self.employee.id,
            'leaving_type_id': self.env.ref('hr.departure_fired').id,
            'departure_date': date(2025, 2, 10),
            'notice_respect': 'without',
            'departure_description': 'foo',
        })
        self.contract.date_end = date(2025, 10, 2)

        payslips = self.env['hr.payslip'].create([{
            'name': 'Payslip Jan 2025 %s',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 1, 1),
            'date_to': datetime(2025, 1, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 2000,
            })],
        }, {
            'name': 'Payslip Feb 2025',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 2, 1),
            'date_to': datetime(2025, 2, 28),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
        }])
        payslips.compute_sheet()

        termination_payslip_id = departure_notice.compute_termination_fee()['res_id']
        termination_fees_payslip = self.env['hr.payslip'].browse(termination_payslip_id)
        termination_fees_payslip.compute_sheet()

        holiday_attests = self.env['hr.payslip.employee.depature.holiday.attests'].with_context(
            active_id=self.employee.id).create({})
        holiday_attests.write(holiday_attests.with_context(active_id=self.employee.id).default_get(holiday_attests._fields))
        holiday_payslip_ids = holiday_attests.compute_termination_holidays()['domain'][0][2]
        holiday_payslips = self.env['hr.payslip'].browse(holiday_payslip_ids)

        thirteen_month_payslip = self.env['hr.payslip'].create({
            'name': 'Thirteen Month Departure',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 2, 1),
            'date_to': datetime(2025, 2, 28),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_thirteen_month').id,
            'company_id': self.belgian_company.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.input_double_holiday_nbr_months').id,
                'amount': 8,
            })],
        })
        thirteen_month_payslip.compute_sheet()
        (payslips + termination_fees_payslip + holiday_payslips + thirteen_month_payslip).action_payslip_done()

        dmfa_dict = self._generate_dmfa_declaration()
        expected_dict = {'DmfAOriginal': {'@{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation': 'DmfAOriginal_20211.xsd', 'Form': {'Identification': 'DMFA', 'FormCreationDate': '2025-04-10', 'FormCreationHour': '10:00:00.000', 'AttestationStatus': '0', 'TypeForm': 'SU', 'Reference': {'ReferenceType': '1', 'ReferenceOrigin': '1', 'ReferenceNbr': 'TESTDMFA'}, 'EmployerDeclaration': {'Quarter': '20251', 'NOSSRegistrationNbr': '123456789', 'Trusteeship': '0', 'CompanyID': '0123456789', 'NetOwedAmount': '00001135206', 'System5': '0', 'NaturalPerson': {'NaturalPersonSequenceNbr': '1', 'INSS': '91111111192', 'NaturalPersonUserReference': str(self.employee.id), 'WorkerRecord': {'EmployerClass': '010', 'WorkerCode': '495', 'NOSSQuarterStartingDate': '2025-01-01', 'NOSSQuarterEndingDate': '2025-03-31', 'Border': '0', 'Occupation': [{'OccupationSequenceNbr': '1', 'OccupationStartingDate': '2018-12-31', 'OccupationEndingDate': '2025-02-10', 'JointCommissionNbr': '200', 'WorkingDaysSystem': '500', 'ContractType': '0', 'RefMeanWorkingHours': '3800', 'MeanWorkingHours': '3800', 'Retired': '0', 'OccupationUserReference': str(self.contract.id), 'LocalUnitID': '0000000123', 'Service': {'ServiceSequenceNbr': '1', 'ServiceCode': '001', 'ServiceNbrDays': '04300', 'ServiceNbrHours': '32680'}, 'Remun': [{'RemunSequenceNbr': '1', 'RemunCode': '001', 'RemunAmount': '00000601800'}, {'RemunSequenceNbr': '2', 'RemunCode': '010', 'RemunAmount': '00000031920'}, {'RemunSequenceNbr': '3', 'RemunCode': '007', 'RemunAmount': '00000061498'}, {'RemunSequenceNbr': '4', 'RemunCode': '002', 'BonusPaymentFrequency': '12', 'RemunAmount': '00000200000'}, {'RemunSequenceNbr': '5', 'RemunCode': '002', 'BonusPaymentFrequency': '00', 'RemunAmount': '00000200000'}], 'OccupationDeduction': {'DeductionCode': '3000', 'DeductionAmount': '00000000000'}}, {'OccupationSequenceNbr': '90', 'OccupationStartingDate': '2025-02-10', 'OccupationEndingDate': '2025-02-10', 'JointCommissionNbr': '200', 'WorkingDaysSystem': '500', 'ContractType': '0', 'RefMeanWorkingHours': '3800', 'MeanWorkingHours': '3800', 'Retired': '0', 'OccupationUserReference': str(self.contract.id), 'LocalUnitID': '0000000123', 'Service': {'ServiceSequenceNbr': '99', 'ServiceCode': '001', 'ServiceNbrDays': '00100', 'ServiceNbrHours': '00760'}, 'Remun': {'RemunSequenceNbr': '99', 'RemunCode': '003', 'RemunAmount': '00001835105'}, 'OccupationDeduction': {'DeductionCode': '3000', 'DeductionAmount': '00000000000'}}], 'WorkerContribution': [{'ContributionWorkerCode': '256', 'ContributionType': '0', 'ContributionCalculationBasis': '00002898403', 'ContributionAmount': '00000000290'}, {'ContributionWorkerCode': '255', 'ContributionType': '0', 'ContributionCalculationBasis': '00002898403', 'ContributionAmount': '00000000580'}, {'ContributionWorkerCode': '495', 'ContributionType': '0', 'ContributionCalculationBasis': '00002898403', 'ContributionAmount': '00001103422'}, {'ContributionWorkerCode': '809', 'ContributionType': '5', 'ContributionCalculationBasis': '00002898403', 'ContributionAmount': '00000005217'}, {'ContributionWorkerCode': '810', 'ContributionType': '0', 'ContributionCalculationBasis': '00002898403', 'ContributionAmount': '00000004927'}, {'ContributionWorkerCode': '831', 'ContributionType': '0', 'ContributionCalculationBasis': '00002898403', 'ContributionAmount': '00000006666'}, {'ContributionWorkerCode': '856', 'ContributionType': '0', 'ContributionAmount': '00000003848'}, {'ContributionWorkerCode': '859', 'ContributionType': '0', 'ContributionCalculationBasis': '00002898403', 'ContributionAmount': '00000002898'}], 'WorkerDeduction': {'DeductionCode': '0001', 'DeductionAmount': '00000006412'}}}, 'CompanyVehicle': {'CompanyVehicleSequenceNbr': '1', 'LicensePlate': 'TEST'}, 'ContributionUnrelatedToNP': [{'UnrelatedEmployerClass': '010', 'UnrelatedWorkerCode': '862', 'UnrelatedAmount': '00000006644'}, {'UnrelatedEmployerClass': '010', 'UnrelatedWorkerCode': '870', 'UnrelatedCalculationBasis': '00000054522', 'UnrelatedAmount': '00000007126'}]}}}}
        self.assertDictEqual(dmfa_dict, expected_dict)

    @freeze_time("2025-04-10 10:00:00")
    def test_07_declaration_employee_notice_period(self):
        departure_notice = self.env['hr.payslip.employee.depature.notice'].create({
            'employee_id': self.employee.id,
            'leaving_type_id': self.env.ref('hr.departure_fired').id,
            'departure_date': date(2025, 2, 10),
            'notice_respect': 'with',
            'departure_description': 'foo',
        })
        self.contract.date_end = date(2025, 10, 2)

        payslips = self.env['hr.payslip'].create([{
            'name': 'Payslip Jan 2025 %s',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 1, 1),
            'date_to': datetime(2025, 1, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 2000,
            })],
        }, {
            'name': 'Payslip Feb 2025',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 2, 1),
            'date_to': datetime(2025, 2, 28),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
        }])
        payslips.compute_sheet()

        termination_payslip_id = departure_notice.compute_termination_fee()['res_id']
        termination_fees_payslip = self.env['hr.payslip'].browse(termination_payslip_id)
        termination_fees_payslip.compute_sheet()

        holiday_attests = self.env['hr.payslip.employee.depature.holiday.attests'].with_context(
            active_id=self.employee.id).create({})
        holiday_attests.write(holiday_attests.with_context(active_id=self.employee.id).default_get(holiday_attests._fields))
        holiday_payslip_ids = holiday_attests.compute_termination_holidays()['domain'][0][2]
        holiday_payslips = self.env['hr.payslip'].browse(holiday_payslip_ids)

        thirteen_month_payslip = self.env['hr.payslip'].create({
            'name': 'Thirteen Month Departure',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 2, 1),
            'date_to': datetime(2025, 2, 28),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_thirteen_month').id,
            'company_id': self.belgian_company.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.input_double_holiday_nbr_months').id,
                'amount': 8,
            })],
        })
        thirteen_month_payslip.compute_sheet()
        (payslips + termination_fees_payslip + holiday_payslips + thirteen_month_payslip).action_payslip_done()

        dmfa_dict = self._generate_dmfa_declaration()
        expected_dict = {'DmfAOriginal': {'@{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation': 'DmfAOriginal_20211.xsd', 'Form': {'Identification': 'DMFA', 'FormCreationDate': '2025-04-10', 'FormCreationHour': '10:00:00.000', 'AttestationStatus': '0', 'TypeForm': 'SU', 'Reference': {'ReferenceType': '1', 'ReferenceOrigin': '1', 'ReferenceNbr': 'TESTDMFA'}, 'EmployerDeclaration': {'Quarter': '20251', 'NOSSRegistrationNbr': '123456789', 'Trusteeship': '0', 'CompanyID': '0123456789', 'NetOwedAmount': '00001104232', 'System5': '0', 'NaturalPerson': {'NaturalPersonSequenceNbr': '1', 'INSS': '91111111192', 'NaturalPersonUserReference': str(self.employee.id), 'WorkerRecord': {'EmployerClass': '010', 'WorkerCode': '495', 'NOSSQuarterStartingDate': '2025-01-01', 'NOSSQuarterEndingDate': '2025-03-31', 'Border': '0', 'Occupation': [{'OccupationSequenceNbr': '1', 'OccupationStartingDate': '2018-12-31', 'OccupationEndingDate': '2025-07-13', 'JointCommissionNbr': '200', 'WorkingDaysSystem': '500', 'ContractType': '0', 'RefMeanWorkingHours': '3800', 'MeanWorkingHours': '3800', 'Retired': '0', 'OccupationUserReference': str(self.contract.id), 'LocalUnitID': '0000000123', 'Service': {'ServiceSequenceNbr': '1', 'ServiceCode': '001', 'ServiceNbrDays': '04300', 'ServiceNbrHours': '32680'}, 'Remun': [{'RemunSequenceNbr': '1', 'RemunCode': '001', 'RemunAmount': '00000601800'}, {'RemunSequenceNbr': '2', 'RemunCode': '010', 'RemunAmount': '00000031920'}, {'RemunSequenceNbr': '3', 'RemunCode': '002', 'BonusPaymentFrequency': '12', 'RemunAmount': '00000200000'}, {'RemunSequenceNbr': '4', 'RemunCode': '002', 'BonusPaymentFrequency': '00', 'RemunAmount': '00000200000'}], 'OccupationDeduction': {'DeductionCode': '3000', 'DeductionAmount': '00000000000'}}, {'OccupationSequenceNbr': '90', 'OccupationStartingDate': '2025-02-17', 'OccupationEndingDate': '2025-03-31', 'JointCommissionNbr': '200', 'WorkingDaysSystem': '500', 'ContractType': '0', 'RefMeanWorkingHours': '3800', 'MeanWorkingHours': '3800', 'Retired': '0', 'OccupationUserReference': str(self.contract.id), 'LocalUnitID': '0000000123', 'Service': {'ServiceSequenceNbr': '99', 'ServiceCode': '001', 'ServiceNbrDays': '03100', 'ServiceNbrHours': '23560'}, 'Remun': {'RemunSequenceNbr': '99', 'RemunCode': '003', 'RemunAmount': '00000611702'}, 'OccupationDeduction': {'DeductionCode': '3000', 'DeductionAmount': '00000000000'}}, {'OccupationSequenceNbr': '91', 'OccupationStartingDate': '2025-04-01', 'OccupationEndingDate': '2025-06-30', 'JointCommissionNbr': '200', 'WorkingDaysSystem': '500', 'ContractType': '0', 'RefMeanWorkingHours': '3800', 'MeanWorkingHours': '3800', 'Retired': '0', 'OccupationUserReference': str(self.contract.id), 'LocalUnitID': '0000000123', 'Service': {'ServiceSequenceNbr': '99', 'ServiceCode': '001', 'ServiceNbrDays': '06500', 'ServiceNbrHours': '49400'}, 'Remun': {'RemunSequenceNbr': '99', 'RemunCode': '003', 'RemunAmount': '00000611702'}, 'OccupationDeduction': {'DeductionCode': '3000', 'DeductionAmount': '00000000000'}}, {'OccupationSequenceNbr': '92', 'OccupationStartingDate': '2025-07-01', 'OccupationEndingDate': '2025-07-13', 'JointCommissionNbr': '200', 'WorkingDaysSystem': '500', 'ContractType': '0', 'RefMeanWorkingHours': '3800', 'MeanWorkingHours': '3800', 'Retired': '0', 'OccupationUserReference': str(self.contract.id), 'LocalUnitID': '0000000123', 'Service': {'ServiceSequenceNbr': '99', 'ServiceCode': '001', 'ServiceNbrDays': '00900', 'ServiceNbrHours': '06840'}, 'Remun': {'RemunSequenceNbr': '99', 'RemunCode': '003', 'RemunAmount': '00000611702'}, 'OccupationDeduction': {'DeductionCode': '3000', 'DeductionAmount': '00000000000'}}], 'WorkerContribution': [{'ContributionWorkerCode': '256', 'ContributionType': '0', 'ContributionCalculationBasis': '00002836905', 'ContributionAmount': '00000000284'}, {'ContributionWorkerCode': '255', 'ContributionType': '0', 'ContributionCalculationBasis': '00002836905', 'ContributionAmount': '00000000567'}, {'ContributionWorkerCode': '495', 'ContributionType': '0', 'ContributionCalculationBasis': '00002836905', 'ContributionAmount': '00001080010'}, {'ContributionWorkerCode': '809', 'ContributionType': '5', 'ContributionCalculationBasis': '00002836905', 'ContributionAmount': '00000005106'}, {'ContributionWorkerCode': '810', 'ContributionType': '0', 'ContributionCalculationBasis': '00002836905', 'ContributionAmount': '00000004823'}, {'ContributionWorkerCode': '831', 'ContributionType': '0', 'ContributionCalculationBasis': '00002836905', 'ContributionAmount': '00000006525'}, {'ContributionWorkerCode': '856', 'ContributionType': '0', 'ContributionAmount': '00000003848'}, {'ContributionWorkerCode': '859', 'ContributionType': '0', 'ContributionCalculationBasis': '00002836905', 'ContributionAmount': '00000002837'}], 'WorkerDeduction': {'DeductionCode': '0001', 'DeductionAmount': '00000006412'}}}, 'CompanyVehicle': {'CompanyVehicleSequenceNbr': '1', 'LicensePlate': 'TEST'}, 'ContributionUnrelatedToNP': [{'UnrelatedEmployerClass': '010', 'UnrelatedWorkerCode': '862', 'UnrelatedAmount': '00000006644'}, {'UnrelatedEmployerClass': '010', 'UnrelatedWorkerCode': '870', 'UnrelatedCalculationBasis': '00000000000', 'UnrelatedAmount': '00000000000'}]}}}}
        self.assertDictEqual(dmfa_dict, expected_dict)

    @freeze_time("2025-04-10 10:00:00")
    def test_08_declaration_structural_reductions_3000(self):
        self.contract.wage_on_signature = 2000
        payslips = self.env['hr.payslip'].create([{
            'name': 'Payslip Jan 2025 %s',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 1, 1),
            'date_to': datetime(2025, 1, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 2000,
            })],
        }, {
            'name': 'Payslip Feb 2025',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 2, 1),
            'date_to': datetime(2025, 2, 28),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
        }, {
            'name': 'Payslip Mar 2025',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 3, 1),
            'date_to': datetime(2025, 3, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
        }])
        payslips.compute_sheet()
        payslips.action_payslip_done()
        dmfa_dict = self._generate_dmfa_declaration()
        expected_dict = {'DmfAOriginal': {'@{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation': 'DmfAOriginal_20211.xsd', 'Form': {'Identification': 'DMFA', 'FormCreationDate': '2025-04-10', 'FormCreationHour': '10:00:00.000', 'AttestationStatus': '0', 'TypeForm': 'SU', 'Reference': {'ReferenceType': '1', 'ReferenceOrigin': '1', 'ReferenceNbr': 'TESTDMFA'}, 'EmployerDeclaration': {'Quarter': '20251', 'NOSSRegistrationNbr': '123456789', 'Trusteeship': '0', 'CompanyID': '0123456789', 'NetOwedAmount': '00000229863', 'System5': '0', 'NaturalPerson': {'NaturalPersonSequenceNbr': '1', 'INSS': '91111111192', 'NaturalPersonUserReference': str(self.employee.id), 'WorkerRecord': {'EmployerClass': '010', 'WorkerCode': '495', 'NOSSQuarterStartingDate': '2025-01-01', 'NOSSQuarterEndingDate': '2025-03-31', 'Border': '0', 'Occupation': {'OccupationSequenceNbr': '1', 'OccupationStartingDate': '2018-12-31', 'JointCommissionNbr': '200', 'WorkingDaysSystem': '500', 'ContractType': '0', 'RefMeanWorkingHours': '3800', 'MeanWorkingHours': '3800', 'Retired': '0', 'OccupationUserReference': str(self.contract.id), 'LocalUnitID': '0000000123', 'Service': {'ServiceSequenceNbr': '1', 'ServiceCode': '001', 'ServiceNbrDays': '06400', 'ServiceNbrHours': '48640'}, 'Remun': [{'RemunSequenceNbr': '1', 'RemunCode': '001', 'RemunAmount': '00000602700'}, {'RemunSequenceNbr': '2', 'RemunCode': '010', 'RemunAmount': '00000047880'}, {'RemunSequenceNbr': '3', 'RemunCode': '002', 'BonusPaymentFrequency': '00', 'RemunAmount': '00000200000'}], 'OccupationDeduction': {'DeductionCode': '3000', 'DeductionAmount': '00000039565'}}, 'WorkerContribution': [{'ContributionWorkerCode': '256', 'ContributionType': '0', 'ContributionCalculationBasis': '00000802700', 'ContributionAmount': '00000000080'}, {'ContributionWorkerCode': '255', 'ContributionType': '0', 'ContributionCalculationBasis': '00000802700', 'ContributionAmount': '00000000161'}, {'ContributionWorkerCode': '495', 'ContributionType': '0', 'ContributionCalculationBasis': '00000802700', 'ContributionAmount': '00000305588'}, {'ContributionWorkerCode': '809', 'ContributionType': '5', 'ContributionCalculationBasis': '00000802700', 'ContributionAmount': '00000001445'}, {'ContributionWorkerCode': '810', 'ContributionType': '0', 'ContributionCalculationBasis': '00000802700', 'ContributionAmount': '00000001365'}, {'ContributionWorkerCode': '831', 'ContributionType': '0', 'ContributionCalculationBasis': '00000802700', 'ContributionAmount': '00000001846'}, {'ContributionWorkerCode': '856', 'ContributionType': '0', 'ContributionAmount': '00000000690'}, {'ContributionWorkerCode': '859', 'ContributionType': '0', 'ContributionCalculationBasis': '00000802700', 'ContributionAmount': '00000000803'}], 'WorkerDeduction': {'DeductionCode': '0001', 'DeductionAmount': '00000052516'}}}, 'CompanyVehicle': {'CompanyVehicleSequenceNbr': '1', 'LicensePlate': 'TEST'}, 'ContributionUnrelatedToNP': [{'UnrelatedEmployerClass': '010', 'UnrelatedWorkerCode': '862', 'UnrelatedAmount': '00000009966'}, {'UnrelatedEmployerClass': '010', 'UnrelatedWorkerCode': '870', 'UnrelatedCalculationBasis': '00000000000', 'UnrelatedAmount': '00000000000'}]}}}}
        self.assertDictEqual(dmfa_dict, expected_dict)

    @freeze_time("2025-04-10 10:00:00")
    def test_90_dmfa_sftp_flow_invalid_acrf(self):
        payslips = self.env['hr.payslip'].create([{
            'name': 'Payslip Jan 2025 %s',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 1, 1),
            'date_to': datetime(2025, 1, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 2000,
            })],
        }, {
            'name': 'Payslip Feb 2025',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 2, 1),
            'date_to': datetime(2025, 2, 28),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
        }, {
            'name': 'Payslip Mar 2025',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 3, 1),
            'date_to': datetime(2025, 3, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
        }])
        payslips.compute_sheet()
        payslips.action_payslip_done()

        # Generate DmfA record
        self.belgian_company.onss_certificate_id = self.env['certificate.certificate'].create({})
        dmfa = self._generate_dmfa_declaration(file_type='T', return_declaration=True, skip_signature=False).with_context(bin_size=False)
        self.assertTrue(dmfa.dmfa_xml)
        self.assertTrue(dmfa.dmfa_go)
        self.assertTrue(dmfa.dmfa_signature)

        # 1. Generate DmfA SFTP declaration, invalid ACRF
        dmfa.action_create_onss_declaration()
        declaration = dmfa.onss_declaration_ids
        self.assertEqual(dmfa.onss_declaration_count, 1)
        self.assertEqual(declaration.onss_file_count, 3)

        # Post DmfA SFTP declaration to ONSS
        with patch('odoo.addons.l10n_be_hr_payroll_dmfa_sftp.models.l10n_be_onss_declaration.open_sftp_connection') as mock_open_conn:
            fake_sftp = MagicMock()
            fake_sftp.putfo = MagicMock()
            # This mock needs to simulate the context manager behavior, specifically the __enter__ and __exit__ methods
            mock_open_conn.return_value.__enter__.return_value = fake_sftp
            mock_open_conn.return_value.__exit__.return_value = None
            declaration.action_post()
            mock_open_conn.assert_called_once()
            fake_sftp.putfo.assert_called()

        self.assertEqual(declaration.state, 'posted')

        # Receive ACRF, signaling an invalid signature
        def mock_listdir_declaration_1(folder):
            if folder in ('OUT', 'OUTTEST-S'):
                return []
            elif folder == 'OUTTEST':
                return [
                    'FO.ACRF.999999.20250410.99999.T',
                    'FS.ACRF.999999.20250410.99999.T',
                    'GO.ACRF.999999.20250410.99999.T',
                ]

        def make_file_mock(return_bytes):
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = return_bytes
            return mock_file

        def file_side_effect_declaration_1(remote_path, mode='rb'):
            if remote_path.endswith('FO.ACRF.999999.20250410.99999.T'):
                xml_str = """<?xml version="1.0" encoding="UTF-8"?>
<ACRF xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="ACRF_20251.xsd">
    <Form>
        <Identification>ACRF001</Identification>
        <FormCreationDate>2025-04-10</FormCreationDate>
        <FormCreationHour>15:36:40.276</FormCreationHour>
        <AttestationStatus>0</AttestationStatus>
        <TypeForm>FA</TypeForm>
        <FileReference>
            <FileName>%(go_filename)s</FileName>
            <ReferenceOrigin>2</ReferenceOrigin>
            <ReferenceNbr>03804UDVFMW3Z</ReferenceNbr>
        </FileReference>
        <ReceptionResult>
            <ResultCode>0</ResultCode>
            <ErrorID>ACRF-125</ErrorID>
        </ReceptionResult>
    </Form>
</ACRF>""" % {'go_filename': dmfa.dmfa_go_filename}
                return make_file_mock(xml_str.encode('utf-8'))
            if remote_path.endswith('FS.ACRF.999999.20250410.99999.T'):
                return make_file_mock(b"dummy\r\nsignature\r\n")
            if remote_path.endswith('GO.ACRF.999999.20250410.99999.T'):
                return make_file_mock(b"")
            raise FileNotFoundError(f"No mock for file: {remote_path}")

        with patch('odoo.addons.l10n_be_hr_payroll_dmfa_sftp.models.l10n_be_onss_declaration.open_sftp_connection') as mock_open_conn:
            fake_sftp = MagicMock()
            fake_sftp.listdir.side_effect = mock_listdir_declaration_1
            fake_sftp.file.side_effect = file_side_effect_declaration_1

            mock_open_conn.return_value.__enter__.return_value = fake_sftp

            declaration._fetch_files()

            assert fake_sftp.file.call_count == 3
            fake_sftp.file.assert_any_call('OUTTEST/FO.ACRF.999999.20250410.99999.T', mode='rb')
            fake_sftp.file.assert_any_call('OUTTEST/FS.ACRF.999999.20250410.99999.T', mode='rb')
            fake_sftp.file.assert_any_call('OUTTEST/GO.ACRF.999999.20250410.99999.T', mode='rb')

        self.assertEqual(declaration.state, 'error')
        self.assertEqual(declaration.error_message, 'ACRF-125\nInvalid signature')
        self.assertEqual(declaration.onss_file_count, 6)

    @freeze_time("2025-04-10 10:00:00")
    def test_91_dmfa_sftp_flow_invalid_noti(self):
        payslips = self.env['hr.payslip'].create([{
            'name': 'Payslip Jan 2025 %s',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 1, 1),
            'date_to': datetime(2025, 1, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 2000,
            })],
        }, {
            'name': 'Payslip Feb 2025',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 2, 1),
            'date_to': datetime(2025, 2, 28),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
        }, {
            'name': 'Payslip Mar 2025',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 3, 1),
            'date_to': datetime(2025, 3, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
        }])
        payslips.compute_sheet()
        payslips.action_payslip_done()

        # Generate DmfA record
        self.belgian_company.onss_certificate_id = self.env['certificate.certificate'].create({})
        dmfa = self._generate_dmfa_declaration(file_type='T', return_declaration=True, skip_signature=False).with_context(bin_size=False)
        self.assertTrue(dmfa.dmfa_xml)
        self.assertTrue(dmfa.dmfa_go)
        self.assertTrue(dmfa.dmfa_signature)

        # Generate DmfA SFTP declaration, valid ACRF
        dmfa.action_create_onss_declaration()
        declaration = dmfa.onss_declaration_ids
        self.assertEqual(dmfa.onss_declaration_count, 1)
        self.assertEqual(declaration.onss_file_count, 3)

        # Post DmfA SFTP declaration to ONSS
        with patch('odoo.addons.l10n_be_hr_payroll_dmfa_sftp.models.l10n_be_onss_declaration.open_sftp_connection') as mock_open_conn:
            fake_sftp = MagicMock()
            fake_sftp.putfo = MagicMock()
            # This mock needs to simulate the context manager behavior, specifically the __enter__ and __exit__ methods
            mock_open_conn.return_value.__enter__.return_value = fake_sftp
            mock_open_conn.return_value.__exit__.return_value = None
            declaration.action_post()
            mock_open_conn.assert_called_once()
            fake_sftp.putfo.assert_called()

        self.assertEqual(declaration.state, 'posted')

        # Receive ACRF, ok
        def mock_listdir_declaration_2(folder):
            if folder == 'OUTTEST':
                return [
                    'FO.ACRF.999999.20250410.99998.T',
                    'FS.ACRF.999999.20250410.99998.T',
                    'GO.ACRF.999999.20250410.99998.T',
                ]
            return []

        def make_file_mock(return_bytes):
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = return_bytes
            return mock_file

        def file_side_effect_declaration_2(remote_path, mode='rb'):
            if remote_path.endswith('FO.ACRF.999999.20250410.99998.T'):
                xml_str = """<?xml version="1.0" encoding="UTF-8"?>
<ACRF xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="ACRF_20251.xsd">
    <Form>
        <Identification>ACRF001</Identification>
        <FormCreationDate>2025-04-10</FormCreationDate>
        <FormCreationHour>12:05:55.075</FormCreationHour>
        <AttestationStatus>0</AttestationStatus>
        <TypeForm>FA</TypeForm>
        <FileReference>
            <FileName>%(go_filename)s</FileName>
            <ReferenceOrigin>2</ReferenceOrigin>
            <ReferenceNbr>03804UE9XCMQZ</ReferenceNbr>
        </FileReference>
        <ReceptionResult>
            <ResultCode>1</ResultCode>
        </ReceptionResult>
    </Form>
</ACRF>""" % {'go_filename': dmfa.dmfa_go_filename}
                return make_file_mock(xml_str.encode('utf-8'))
            if remote_path.endswith('FS.ACRF.999999.20250410.99998.T'):
                return make_file_mock(b"dummy\r\nsignature\r\n")
            if remote_path.endswith('GO.ACRF.999999.20250410.99998.T'):
                return make_file_mock(b"")
            raise FileNotFoundError(f"No mock for file: {remote_path}")

        with patch('odoo.addons.l10n_be_hr_payroll_dmfa_sftp.models.l10n_be_onss_declaration.open_sftp_connection') as mock_open_conn:
            fake_sftp = MagicMock()
            fake_sftp.listdir.side_effect = mock_listdir_declaration_2
            fake_sftp.file.side_effect = file_side_effect_declaration_2

            mock_open_conn.return_value.__enter__.return_value = fake_sftp

            declaration._fetch_files()

            assert fake_sftp.file.call_count == 3
            fake_sftp.file.assert_any_call('OUTTEST/FO.ACRF.999999.20250410.99998.T', mode='rb')
            fake_sftp.file.assert_any_call('OUTTEST/FS.ACRF.999999.20250410.99998.T', mode='rb')
            fake_sftp.file.assert_any_call('OUTTEST/GO.ACRF.999999.20250410.99998.T', mode='rb')

        self.assertEqual(declaration.state, 'received')
        self.assertFalse(declaration.error_message)
        self.assertEqual(declaration.onss_file_count, 6)

        # Receive Notification, signaling an invalid declaration (blocking anomaly)
        def mock_listdir_notification_1(folder):
            if folder in ('OUT', 'OUTTEST-S'):
                return []
            elif folder == 'OUTTEST':
                return [
                    'FO.NOTI.999999.20250410.99998.T',
                    'FS.NOTI.999999.20250410.99998.T',
                    'GO.NOTI.999999.20250410.99998.T',
                ]

        def file_side_effect_notification_1(remote_path, mode='rb'):
            if remote_path.endswith('FO.NOTI.999999.20250410.99998.T'):
                xml_str = """<?xml version="1.0" encoding="UTF-8"?><NOTIFICATION xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="NOTIFICATION_20251.xsd">
  <Form>
    <Identification>NOTI001</Identification>
    <FormCreationDate>2025-04-10</FormCreationDate>
    <FormCreationHour>16:35:16.359</FormCreationHour>
    <AttestationStatus>0</AttestationStatus>
    <TypeForm>FA</TypeForm>
    <FileReference>
      <FileName>%(go_filename)s</FileName>
      <ReferenceOrigin>2</ReferenceOrigin>
      <ReferenceNbr>03804UAVJS3PZ</ReferenceNbr>
    </FileReference>
    <HandledOriginalForm>
      <Identification>DMFA</Identification>
      <FormCreationDate>2025-04-10</FormCreationDate>
      <FormCreationHour>14:34:30.000</FormCreationHour>
      <AttestationStatus>0</AttestationStatus>
      <TypeForm>SU</TypeForm>
    </HandledOriginalForm>
    <Reference>
      <ReferenceType>1</ReferenceType>
      <ReferenceOrigin>1</ReferenceOrigin>
      <ReferenceNbr>2025/1</ReferenceNbr>
    </Reference>
    <EmployerId>
      <NOSSRegistrationNbr>123456789</NOSSRegistrationNbr>
      <CompanyID>0123456789</CompanyID>
    </EmployerId>
    <ConcernedQuarter>
      <Quarter>20251</Quarter>
    </ConcernedQuarter>
    <HandledReference>
      <ReferenceType>1</ReferenceType>
      <ReferenceOrigin>2</ReferenceOrigin>
      <ReferenceNbr>0340822PQ9CMZ</ReferenceNbr>
    </HandledReference>
    <WorkerRecordIdentification>
      <Quarter>20251</Quarter>
      <NOSSRegistrationNbr>123456789</NOSSRegistrationNbr>
      <CompanyID>0123456789</CompanyID>
      <NaturalPersonSequenceNbr>1</NaturalPersonSequenceNbr>
      <INSS>91111111192</INSS>
      <EmployerClass>578</EmployerClass>
      <WorkerCode>495</WorkerCode>
    </WorkerRecordIdentification>
    <HandlingResult>
      <ResultCode>0</ResultCode>
      <AnomalyReport>
        <ErrorID>00011-155</ErrorID>
        <TagName>NOSSRegistrationNbr</TagName>
        <Value>123456789</Value>
        <AnomalyClass>B</AnomalyClass>
        <AnomalyLocation>
          <Location>1,1,7,2</Location>
        </AnomalyLocation>
      </AnomalyReport>
    </HandlingResult>
  </Form>
</NOTIFICATION>""" % {'go_filename': dmfa.dmfa_go_filename}
                return make_file_mock(xml_str.encode('utf-8'))
            if remote_path.endswith('FS.NOTI.999999.20250410.99998.T'):
                return make_file_mock(b"dummy\r\nsignature\r\n")
            if remote_path.endswith('GO.NOTI.999999.20250410.99998.T'):
                return make_file_mock(b"")
            raise FileNotFoundError(f"No mock for file: {remote_path}")

        with patch('odoo.addons.l10n_be_hr_payroll_dmfa_sftp.models.l10n_be_onss_declaration.open_sftp_connection') as mock_open_conn:
            fake_sftp = MagicMock()
            fake_sftp.listdir.side_effect = mock_listdir_notification_1
            fake_sftp.file.side_effect = file_side_effect_notification_1

            mock_open_conn.return_value.__enter__.return_value = fake_sftp

            declaration._fetch_files()

            assert fake_sftp.file.call_count == 3
            fake_sftp.file.assert_any_call('OUTTEST/FO.NOTI.999999.20250410.99998.T', mode='rb')
            fake_sftp.file.assert_any_call('OUTTEST/FS.NOTI.999999.20250410.99998.T', mode='rb')
            fake_sftp.file.assert_any_call('OUTTEST/GO.NOTI.999999.20250410.99998.T', mode='rb')

        self.assertEqual(declaration.state, 'error')
        self.assertEqual(declaration.error_message, 'Declaration rejected - blocking anomalies\nAnomaly (1/1) - Code: 00011-155\nNo or no longer a mandate\n- Tag Name: NOSSRegistrationNbr\n- Value: 123456789\n- NISS: False\n- Anomaly Class: Blocking anomaly\n\n')
        self.assertEqual(declaration.onss_file_count, 9)

    @freeze_time("2025-04-10 10:00:00")
    def test_92_dmfa_sftp_flow_valid_noti(self):
        payslips = self.env['hr.payslip'].create([{
            'name': 'Payslip Jan 2025 %s',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 1, 1),
            'date_to': datetime(2025, 1, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 2000,
            })],
        }, {
            'name': 'Payslip Feb 2025',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 2, 1),
            'date_to': datetime(2025, 2, 28),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
        }, {
            'name': 'Payslip Mar 2025',
            'contract_id': self.contract.id,
            'date_from': datetime(2025, 3, 1),
            'date_to': datetime(2025, 3, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.belgian_company.id,
        }])
        payslips.compute_sheet()
        payslips.action_payslip_done()

        # Generate DmfA record
        self.belgian_company.onss_certificate_id = self.env['certificate.certificate'].create({})
        dmfa = self._generate_dmfa_declaration(file_type='T', return_declaration=True, skip_signature=False).with_context(bin_size=False)
        self.assertTrue(dmfa.dmfa_xml)
        self.assertTrue(dmfa.dmfa_go)
        self.assertTrue(dmfa.dmfa_signature)

        # Generate DmfA SFTP declaration, valid ACRF, valid NOTI
        dmfa.action_create_onss_declaration()
        declaration = dmfa.onss_declaration_ids
        self.assertEqual(dmfa.onss_declaration_count, 1)
        self.assertEqual(declaration.onss_file_count, 3)

        # Post DmfA SFTP declaration to ONSS
        with patch('odoo.addons.l10n_be_hr_payroll_dmfa_sftp.models.l10n_be_onss_declaration.open_sftp_connection') as mock_open_conn:
            fake_sftp = MagicMock()
            fake_sftp.putfo = MagicMock()
            # This mock needs to simulate the context manager behavior, specifically the __enter__ and __exit__ methods
            mock_open_conn.return_value.__enter__.return_value = fake_sftp
            mock_open_conn.return_value.__exit__.return_value = None
            declaration.action_post()
            mock_open_conn.assert_called_once()
            fake_sftp.putfo.assert_called()

        self.assertEqual(declaration.state, 'posted')

        # Receive ACRF, ok
        def mock_listdir_declaration_3(folder):
            if folder == 'OUTTEST':
                return [
                    'FO.ACRF.999999.20250410.99997.T',
                    'FS.ACRF.999999.20250410.99997.T',
                    'GO.ACRF.999999.20250410.99997.T',
                ]
            return []

        def make_file_mock(return_bytes):
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = return_bytes
            return mock_file

        def file_side_effect_declaration_3(remote_path, mode='rb'):
            if remote_path.endswith('FO.ACRF.999999.20250410.99997.T'):
                xml_str = """<?xml version="1.0" encoding="UTF-8"?>
<ACRF xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="ACRF_20251.xsd">
    <Form>
        <Identification>ACRF001</Identification>
        <FormCreationDate>2025-04-10</FormCreationDate>
        <FormCreationHour>12:05:55.075</FormCreationHour>
        <AttestationStatus>0</AttestationStatus>
        <TypeForm>FA</TypeForm>
        <FileReference>
            <FileName>%(go_filename)s</FileName>
            <ReferenceOrigin>2</ReferenceOrigin>
            <ReferenceNbr>03804UE9XCMQZ</ReferenceNbr>
        </FileReference>
        <ReceptionResult>
            <ResultCode>1</ResultCode>
        </ReceptionResult>
    </Form>
</ACRF>""" % {'go_filename': dmfa.dmfa_go_filename}
                return make_file_mock(xml_str.encode('utf-8'))
            if remote_path.endswith('FS.ACRF.999999.20250410.99997.T'):
                return make_file_mock(b"dummy\r\nsignature\r\n")
            if remote_path.endswith('GO.ACRF.999999.20250410.99997.T'):
                return make_file_mock(b"")
            raise FileNotFoundError(f"No mock for file: {remote_path}")

        with patch('odoo.addons.l10n_be_hr_payroll_dmfa_sftp.models.l10n_be_onss_declaration.open_sftp_connection') as mock_open_conn:
            fake_sftp = MagicMock()
            fake_sftp.listdir.side_effect = mock_listdir_declaration_3
            fake_sftp.file.side_effect = file_side_effect_declaration_3

            mock_open_conn.return_value.__enter__.return_value = fake_sftp

            declaration._fetch_files()

            assert fake_sftp.file.call_count == 3
            fake_sftp.file.assert_any_call('OUTTEST/FO.ACRF.999999.20250410.99997.T', mode='rb')
            fake_sftp.file.assert_any_call('OUTTEST/FS.ACRF.999999.20250410.99997.T', mode='rb')
            fake_sftp.file.assert_any_call('OUTTEST/GO.ACRF.999999.20250410.99997.T', mode='rb')

        self.assertEqual(declaration.state, 'received')
        self.assertFalse(declaration.error_message)
        self.assertEqual(declaration.onss_file_count, 6)

        # Receive Notification, signaling an invalid declaration (blocking anomaly)
        def mock_listdir_notification_2(folder):
            if folder in ('OUT', 'OUTTEST-S'):
                return []
            elif folder == 'OUTTEST':
                return [
                    'FO.NOTI.999999.20250410.99997.T',
                    'FS.NOTI.999999.20250410.99997.T',
                    'GO.NOTI.999999.20250410.99997.T',
                ]

        def file_side_effect_notification_2(remote_path, mode='rb'):
            dmfa_onss_file = declaration.onss_file_ids.filtered(lambda f: f.declaration_type == 'DMFA' and f.file_type == 'FI')
            if remote_path.endswith('FO.NOTI.999999.20250410.99997.T'):
                xml_str = """<?xml version="1.0" encoding="UTF-8"?><NOTIFICATION xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="NOTIFICATION_20251.xsd">
<Form>
    <Identification>NOTI001</Identification>
    <FormCreationDate>2025-04-10</FormCreationDate>
    <FormCreationHour>21:48:14.795</FormCreationHour>
    <AttestationStatus>0</AttestationStatus>
    <TypeForm>FA</TypeForm>
    <HandledOriginalForm>
      <Identification>DMFA</Identification>
      <FormCreationDate>%(form_creation_date)s</FormCreationDate>
      <FormCreationHour>%(form_creation_hour)s</FormCreationHour>
      <AttestationStatus>0</AttestationStatus>
      <TypeForm>SU</TypeForm>
    </HandledOriginalForm>
    <Reference>
      <ReferenceType>1</ReferenceType>
      <ReferenceOrigin>1</ReferenceOrigin>
      <ReferenceNbr>2025/1</ReferenceNbr>
    </Reference>
<EmployerId>
      <NOSSRegistrationNbr>123456789</NOSSRegistrationNbr>
      <CompanyID>0123456789</CompanyID>
    </EmployerId>
    <ConcernedQuarter>
      <Quarter>20251</Quarter>
    </ConcernedQuarter>
<HandledReference>
      <ReferenceType>1</ReferenceType>
      <ReferenceOrigin>2</ReferenceOrigin>
      <ReferenceNbr>034081YBAQWPZ</ReferenceNbr>
    </HandledReference>
    <DeclarationComplInformations>
      <DMFAWorkersNbr>1</DMFAWorkersNbr>
      <DIMONAWorkersNbr>1</DIMONAWorkersNbr>
    </DeclarationComplInformations>
    <HandlingResult>
      <ResultCode>1</ResultCode>
      <AnomalyReport>
        <ErrorID>90007-262</ErrorID>
        <AnomalyClass>NP</AnomalyClass>
        <AnomalyLabel>Déclaration employeur - Plus de travailleurs déclarés en DmfA qu'en DIMONA</AnomalyLabel>
        <Path>
          <Quarter>20251</Quarter>
          <NOSSRegistrationNbr>123456789</NOSSRegistrationNbr>
          <Trusteeship>0</Trusteeship>
          <CompanyID>0123456789</CompanyID>
        </Path>
      </AnomalyReport>
      <AnomalyReport>
        <ErrorID>90001-476</ErrorID>
        <AnomalyClass>NP</AnomalyClass>
        <AnomalyLabel>Cotisation due pour la ligne travailleur - Cotisation spéciale sur les indemnités de rupture non présente</AnomalyLabel>
        <Path>
          <Quarter>20251</Quarter>
          <NOSSRegistrationNbr>123456789</NOSSRegistrationNbr>
          <Trusteeship>0</Trusteeship>
          <CompanyID>0123456789</CompanyID>
          <NaturalPersonSequenceNbr>1</NaturalPersonSequenceNbr>
          <INSS>91111111192</INSS>
          <EmployerClass>010</EmployerClass>
          <WorkerCode>495</WorkerCode>
          <NaturalPersonUserReference>4482041</NaturalPersonUserReference>
        </Path>
      </AnomalyReport>
    </HandlingResult>
  </Form>
</NOTIFICATION>""" % {'form_creation_date': dmfa_onss_file.form_creation_date, 'form_creation_hour': dmfa_onss_file.form_creation_hour}
                return make_file_mock(xml_str.encode('utf-8'))
            if remote_path.endswith('FS.NOTI.999999.20250410.99997.T'):
                return make_file_mock(b"dummy\r\nsignature\r\n")
            if remote_path.endswith('GO.NOTI.999999.20250410.99997.T'):
                return make_file_mock(b"")
            raise FileNotFoundError(f"No mock for file: {remote_path}")

        with patch('odoo.addons.l10n_be_hr_payroll_dmfa_sftp.models.l10n_be_onss_declaration.open_sftp_connection') as mock_open_conn:
            fake_sftp = MagicMock()
            fake_sftp.listdir.side_effect = mock_listdir_notification_2
            fake_sftp.file.side_effect = file_side_effect_notification_2

            mock_open_conn.return_value.__enter__.return_value = fake_sftp

            declaration._fetch_files()

            assert fake_sftp.file.call_count == 3
            fake_sftp.file.assert_any_call('OUTTEST/FO.NOTI.999999.20250410.99997.T', mode='rb')
            fake_sftp.file.assert_any_call('OUTTEST/FS.NOTI.999999.20250410.99997.T', mode='rb')
            fake_sftp.file.assert_any_call('OUTTEST/GO.NOTI.999999.20250410.99997.T', mode='rb')

        self.assertEqual(declaration.state, 'notified')
        self.assertEqual(declaration.error_message, 'Anomaly (1/2) - Code: 90007-262\nMore workers declared in DmfA than in DIMONA\n- NISS: False\n- Anomaly Class: Non-percentage-based anomaly\n\n\nAnomaly (2/2) - Code: 90001-476\nSpecial contribution on severance pay not present\n- Employee: Laurie Poiret (NISS: 91111111192)\n- Anomaly Class: Non-percentage-based anomaly\n\n')
        self.assertEqual(declaration.onss_file_count, 9)
