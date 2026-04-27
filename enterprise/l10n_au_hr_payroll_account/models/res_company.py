# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_au_hr_super_responsible_id = fields.Many2one(
        "hr.employee",
        string="HR Super Sender",
        help="The employee responsible for sending Super")

    l10n_au_stp_responsible_id = fields.Many2one("hr.employee", string="STP Responsible")

    @api.constrains('l10n_au_hr_super_responsible_id', 'l10n_au_stp_responsible_id')
    def _check_payroll_responsible_fields(self):
        for company in self:
            if company.l10n_au_hr_super_responsible_id and not company.l10n_au_hr_super_responsible_id.user_id.exists():
                raise ValidationError(_("The HR Super Sender must be linked to a user."))
            if company.l10n_au_stp_responsible_id and not company.l10n_au_stp_responsible_id.user_id.exists():
                raise ValidationError(_("The STP Responsible must be linked to a user."))

    def _create_ytd_values(self, employees, start_date):
        values = []
        default_struct_id = self.env.ref("l10n_au_hr_payroll.hr_payroll_structure_au_regular").id
        for employee in employees:
            if not employee.structure_type_id.default_struct_id:
                raise UserError(_("Unable to generate YTD Opening balance for %s. "
                    "Please set the correct salary structure or unset the Import YTD field.", (employee.name)))
            values += [
                {
                    "employee_id": employee.id,
                    "struct_id": default_struct_id,
                    "requires_inputs": True,
                    "rule_id": self.env["hr.salary.rule"].search(
                        [
                            ("struct_id", "=", default_struct_id),
                            ("code", "=", "BASIC")
                        ],
                        limit=1).id,
                    "start_date": start_date,
                    "l10n_au_payslip_ytd_input_ids": [
                        (0, 0, {
                            "res_id": self.env.ref("hr_work_entry.work_entry_type_attendance").id,
                            "res_model": "hr.work.entry.type",
                            "ytd_amount": 0,
                        }),
                        (0, 0, {
                            "res_id": self.env.ref("hr_work_entry.overtime_work_entry_type").id,
                            "res_model": "hr.work.entry.type",
                            "ytd_amount": 0,
                        }),
                        (0, 0, {
                            "res_id": self.env.ref("l10n_au_hr_payroll.l10n_au_work_entry_type_other").id,
                            "res_model": "hr.work.entry.type",
                            "ytd_amount": 0,
                        }),
                        (0, 0, {
                            "res_id": self.env.ref("l10n_au_hr_payroll.l10n_au_work_entry_type_parental").id,
                            "res_model": "hr.work.entry.type",
                            "ytd_amount": 0,
                        }),
                        (0, 0, {
                            "res_id": self.env.ref("l10n_au_hr_payroll.l10n_au_work_entry_type_compensation").id,
                            "res_model": "hr.work.entry.type",
                            "ytd_amount": 0,
                        }),
                        (0, 0, {
                            "res_id": self.env.ref("l10n_au_hr_payroll.l10n_au_work_entry_type_defence").id,
                            "res_model": "hr.work.entry.type",
                            "ytd_amount": 0,
                        }),
                    ]

                }, {
                    "employee_id": employee.id,
                    "struct_id": default_struct_id,
                    "requires_inputs": True,
                    "rule_id": self.env.ref("l10n_au_hr_payroll.l10n_au_extra_pay_structure_1").id,
                    "start_date": start_date,
                    "l10n_au_payslip_ytd_input_ids": [
                        (0, 0, {
                            "res_id": input_type.id,
                            "res_model": "hr.payslip.input.type",
                        }) for input_type in self.env["hr.payslip.input.type"].search([("code", "=", "EXTRA.INPUT")])
                    ],
                }, {
                    "employee_id": employee.id,
                    "struct_id": default_struct_id,
                    "requires_inputs": True,
                    "rule_id": self.env.ref("l10n_au_hr_payroll.l10n_au_salary_sacrifice_other_structure_1").id,
                    "start_date": start_date,
                    "l10n_au_payslip_ytd_input_ids": [
                        (0, 0, {
                            "res_id": self.env.ref("l10n_au_hr_payroll.input_salary_sacrifice_other"),
                            "res_model": "hr.payslip.input.type",
                        }), (0, 0, {
                            "name": "Salary Sacrificed Workplace Giving",
                        })
                    ],
                }, {
                    "employee_id": employee.id,
                    "struct_id": default_struct_id,
                    "rule_id": self.env.ref("l10n_au_hr_payroll.l10n_au_workplace_giving_structure_1").id,
                    "start_date": start_date,
                }, {
                    "employee_id": employee.id,
                    "struct_id": default_struct_id,
                    "requires_inputs": True,
                    "rule_id": self.env.ref("l10n_au_hr_payroll.l10n_au_allowance_structure_1").id,
                    "start_date": start_date,
                    "l10n_au_payslip_ytd_input_ids": [
                        (0, 0, {
                            "res_id": input_type.id,
                            "res_model": "hr.payslip.input.type",
                        })
                        for input_type in self.env["hr.payslip.input.type"].search(
                            [
                                ("l10n_au_payment_type", "=", "allowance"),
                                ("l10n_au_paygw_treatment", "=", "regular"),
                            ]
                        )
                    ],
                }, {
                    "employee_id": employee.id,
                    "struct_id": default_struct_id,
                    "rule_id": self.env.ref("l10n_au_hr_payroll.l10n_au_return_to_work_structure_1").id,
                    "start_date": start_date,
                }, {
                    "employee_id": employee.id,
                    "struct_id": default_struct_id,
                    "requires_inputs": True,
                    "rule_id": self.env.ref("l10n_au_hr_payroll.l10n_au_non_tax_allowance_structure_1").id,
                    "start_date": start_date,
                    "l10n_au_payslip_ytd_input_ids": [
                        (0, 0, {
                            "res_id": input_type.id,
                            "res_model": "hr.payslip.input.type",
                        })
                        for input_type in self.env["hr.payslip.input.type"].search(
                            [
                                ("l10n_au_payment_type", "=", "allowance"),
                                ("l10n_au_paygw_treatment", "=", "no_paygw"),
                            ]
                        )
                    ],
                }, {
                    "employee_id": employee.id,
                    "struct_id": default_struct_id,
                    "requires_inputs": True,
                    "rule_id": self.env.ref("l10n_au_hr_payroll.l10n_au_back_payments_structure_1").id,
                    "start_date": start_date,
                    "l10n_au_payslip_ytd_input_ids": [
                        (0, 0, {
                            "res_id": input_type.id,
                            "res_model": "hr.payslip.input.type",
                        })
                        for input_type in self.env["hr.payslip.input.type"].search([("code", "=", "BACKPAY.INPUT")])
                    ],
                }, {
                    "employee_id": employee.id,
                    "struct_id": default_struct_id,
                    "rule_id": self.env.ref("l10n_au_hr_payroll.l10n_au_withholding_net_structure_1").id,
                    "start_date": start_date,
                }, {
                    "employee_id": employee.id,
                    "struct_id": default_struct_id,
                    "requires_inputs": True,
                    "rule_id": self.env.ref("l10n_au_hr_payroll.l10n_au_child_support_structure_1").id,
                    "start_date": start_date,
                    "l10n_au_payslip_ytd_input_ids": [
                        (0, 0, {
                            "name": "Child Support Deduction",
                        }),
                    ] + [
                        (0, 0, {
                            "res_id": input_type.id,
                            "res_model": "hr.payslip.input.type",
                        })
                        for input_type in self.env["hr.payslip.input.type"].search([("code", "=", "CHILD_SUPPORT_GARNISHEE")])
                    ],
                }, {
                    "employee_id": employee.id,
                    "struct_id": default_struct_id,
                    "rule_id": self.env.ref("l10n_au_hr_payroll.l10n_au_super_contribution_structure_1").id,
                    "start_date": start_date,
                }, {
                    "employee_id": employee.id,
                    "struct_id": default_struct_id,
                    "requires_inputs": True,
                    "rule_id": self.env.ref("l10n_au_hr_payroll.l10n_au_salary_sacrifice_structure_1").id,
                    "start_date": start_date,
                    "l10n_au_payslip_ytd_input_ids": [
                        (0, 0, {
                            "res_id": self.env.ref("l10n_au_hr_payroll.input_salary_sacrifice_superannuation"),
                            "res_model": "hr.payslip.input.type",
                        }),
                        (0, 0, {
                            "name": "Extra Negotiated Super (RESC)",
                        }),
                        (0, 0, {
                            "name": "Extra Compusory Super (Non RESC)",
                        }),
                    ],
                }, {
                    "employee_id": employee.id,
                    "struct_id": default_struct_id,
                    "requires_inputs": True,
                    "rule_id": self.env.ref("l10n_au_hr_payroll.l10n_au_reportable_fringe_benefits_structure_1").id,
                    "start_date": start_date,
                    "l10n_au_payslip_ytd_input_ids": [
                        (0, 0, {
                            "res_id": input_type.id,
                            "res_model": "hr.payslip.input.type",
                        })
                        for input_type in self.env["hr.payslip.input.type"].search([("code", "=", "FBT")])
                    ],
                }
            ]
        return self.env["l10n_au.payslip.ytd"].create(values)
