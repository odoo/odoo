# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import math
from datetime import date, datetime, time

import babel
from dateutil.relativedelta import relativedelta
from pytz import timezone

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

from .base_browsable import (
    BaseBrowsableObject,
    BrowsableObject,
    InputLine,
    Payslips,
    WorkedDays,
)

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _name = "hr.payslip"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Payslip"
    _order = "id desc"

    struct_id = fields.Many2one(
        "hr.payroll.structure",
        string="Structure",
        readonly=True,
        help="Defines the rules that have to be applied to this payslip, "
        "accordingly to the contract chosen. If you let empty the field "
        "contract, this field isn't mandatory anymore and thus the rules "
        "applied will be all the rules set on the structure of all contracts "
        "of the employee valid for the chosen period",
    )
    name = fields.Char(string="Payslip Name", readonly=True)
    number = fields.Char(
        string="Reference",
        readonly=True,
        copy=False,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        required=True,
        readonly=True,
    )
    date_from = fields.Date(
        readonly=True,
        required=True,
        default=lambda self: fields.Date.to_string(date.today().replace(day=1)),
        tracking=True,
    )
    date_to = fields.Date(
        readonly=True,
        required=True,
        default=lambda self: fields.Date.to_string(
            (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()
        ),
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("verify", "Waiting"),
            ("done", "Done"),
            ("cancel", "Rejected"),
        ],
        string="Status",
        index=True,
        readonly=True,
        copy=False,
        default="draft",
        tracking=True,
        help="""* When the payslip is created the status is \'Draft\'
        \n* If the payslip is under verification, the status is \'Waiting\'.
        \n* If the payslip is confirmed then status is set to \'Done\'.
        \n* When user cancel payslip the status is \'Rejected\'.""",
    )
    line_ids = fields.One2many(
        "hr.payslip.line",
        "slip_id",
        string="Payslip Lines",
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        readonly=True,
        copy=False,
        default=lambda self: self.env.company,
    )
    worked_days_line_ids = fields.One2many(
        "hr.payslip.worked_days",
        "payslip_id",
        string="Payslip Worked Days",
        copy=True,
        readonly=True,
    )
    input_line_ids = fields.One2many(
        "hr.payslip.input",
        "payslip_id",
        string="Payslip Inputs",
        readonly=True,
    )
    paid = fields.Boolean(
        string="Made Payment Order ? ",
        readonly=True,
        copy=False,
    )
    note = fields.Text(
        string="Internal Note",
        readonly=True,
        tracking=True,
    )
    contract_id = fields.Many2one(
        "hr.contract",
        string="Contract",
        readonly=True,
        tracking=True,
    )
    dynamic_filtered_payslip_lines = fields.One2many(
        "hr.payslip.line",
        compute="_compute_dynamic_filtered_payslip_lines",
    )
    credit_note = fields.Boolean(
        readonly=True,
        help="Indicates this payslip has a refund of another",
    )
    payslip_run_id = fields.Many2one(
        "hr.payslip.run",
        string="Payslip Batches",
        readonly=True,
        copy=False,
        tracking=True,
    )
    payslip_count = fields.Integer(
        compute="_compute_payslip_count", string="Payslip Computation Details"
    )
    hide_child_lines = fields.Boolean(default=False)
    hide_invisible_lines = fields.Boolean(
        string="Show only lines that appear on payslip", default=False
    )
    compute_date = fields.Date()
    refunded_id = fields.Many2one(
        "hr.payslip", string="Refunded Payslip", readonly=True
    )
    allow_cancel_payslips = fields.Boolean(
        "Allow Canceling Payslips", compute="_compute_allow_cancel_payslips"
    )
    prevent_compute_on_confirm = fields.Boolean(
        "Prevent Compute on Confirm", compute="_compute_prevent_compute_on_confirm"
    )

    def _compute_allow_cancel_payslips(self):
        self.allow_cancel_payslips = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("payroll.allow_cancel_payslips")
        )

    def _compute_prevent_compute_on_confirm(self):
        self.prevent_compute_on_confirm = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("payroll.prevent_compute_on_confirm")
        )

    @api.depends("line_ids", "hide_child_lines", "hide_invisible_lines")
    def _compute_dynamic_filtered_payslip_lines(self):
        for payslip in self:
            lines = payslip.line_ids
            if payslip.hide_child_lines:
                lines = lines.filtered(lambda line: not line.parent_rule_id)
            if payslip.hide_invisible_lines:
                lines = lines.filtered(lambda line: line.appears_on_payslip)
            payslip.dynamic_filtered_payslip_lines = lines

    def _compute_payslip_count(self):
        for payslip in self:
            payslip.payslip_count = len(payslip.line_ids)

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        if any(self.filtered(lambda payslip: payslip.date_from > payslip.date_to)):
            raise ValidationError(
                _("Payslip 'Date From' must be earlier than 'Date To'.")
            )

    def copy(self, default=None):
        rec = super().copy(default)
        for line in self.input_line_ids:
            line.copy({"payslip_id": rec.id})
        for line in self.line_ids:
            line.copy({"slip_id": rec.id, "input_ids": []})
        return rec

    def action_payslip_draft(self):
        return self.write({"state": "draft"})

    def action_payslip_done(self):
        if (
            not self.env.context.get("without_compute_sheet")
            and not self.prevent_compute_on_confirm
        ):
            self.compute_sheet()
        return self.write({"state": "done"})

    def action_payslip_cancel(self):
        for payslip in self:
            if payslip.allow_cancel_payslips:
                if payslip.refunded_id and payslip.refunded_id.state != "cancel":
                    raise ValidationError(
                        _(
                            """To cancel the Original Payslip the
                        Refunded Payslip needs to be canceled first!"""
                        )
                    )
            else:
                if self.filtered(lambda slip: slip.state == "done"):
                    raise UserError(_("Cannot cancel a payslip that is done."))
        return self.write({"state": "cancel"})

    def refund_sheet(self):
        for payslip in self:
            copied_payslip = payslip.copy(
                {"credit_note": True, "name": _("Refund: %s") % payslip.name}
            )
            number = copied_payslip.number or self.env["ir.sequence"].next_by_code(
                "salary.slip"
            )
            copied_payslip.write({"number": number})
            copied_payslip.with_context(
                without_compute_sheet=True
            ).action_payslip_done()
        formview_ref = self.env.ref("payroll.hr_payslip_view_form", False)
        treeview_ref = self.env.ref("payroll.hr_payslip_view_tree", False)
        res = {
            "name": _("Refund Payslip"),
            "view_mode": "tree, form",
            "view_id": False,
            "res_model": "hr.payslip",
            "type": "ir.actions.act_window",
            "target": "current",
            "domain": "[('id', 'in', %s)]" % copied_payslip.ids,
            "views": [
                (treeview_ref and treeview_ref.id or False, "tree"),
                (formview_ref and formview_ref.id or False, "form"),
            ],
            "context": {},
        }
        payslip.write({"refunded_id": safe_eval(res["domain"])[0][2][0] or False})
        return res

    def unlink(self):
        if any(self.filtered(lambda payslip: payslip.state not in ("draft", "cancel"))):
            raise UserError(
                _("You cannot delete a payslip which is not draft or cancelled")
            )
        return super().unlink()

    def compute_sheet(self):
        for payslip in self:
            # delete old payslip lines
            payslip.line_ids.unlink()
            # write payslip lines
            number = payslip.number or self.env["ir.sequence"].next_by_code(
                "salary.slip"
            )
            lines = [(0, 0, line) for line in list(payslip.get_lines_dict().values())]
            payslip.write(
                {
                    "line_ids": lines,
                    "number": number,
                    "state": "verify",
                    "compute_date": fields.Date.today(),
                }
            )
        return True

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contracts: Browse record of contracts
        @return: returns a list of dict containing the input that should be
        applied for the given contract between date_from and date_to
        """
        res = []
        for contract in contracts.filtered(
            lambda contract: contract.resource_calendar_id
        ):
            day_from = datetime.combine(date_from, time.min)
            day_to = datetime.combine(date_to, time.max)
            day_contract_start = datetime.combine(contract.date_start, time.min)
            # Support for the hr_public_holidays module.
            contract = contract.with_context(
                employee_id=self.employee_id.id, exclude_public_holidays=True
            )
            # only use payslip day_from if it's greather than contract start date
            if day_from < day_contract_start:
                day_from = day_contract_start
            # == compute leave days == #
            leaves = self._compute_leave_days(contract, day_from, day_to)
            res.extend(leaves)
            # == compute worked days == #
            attendances = self._compute_worked_days(contract, day_from, day_to)
            res.append(attendances)
        return res

    def _compute_leave_days(self, contract, day_from, day_to):
        """
        Leave days computation
        @return: returns a list containing the leave inputs for the period
        of the payslip. One record per leave type.
        """
        leaves_positive = (
            self.env["ir.config_parameter"].sudo().get_param("payroll.leaves_positive")
        )
        leaves = {}
        calendar = contract.resource_calendar_id
        tz = timezone(calendar.tz)
        day_leave_intervals = contract.employee_id.list_leaves(
            day_from, day_to, calendar=contract.resource_calendar_id
        )
        for day, hours, leave in day_leave_intervals:
            holiday = leave[:1].holiday_id
            current_leave_struct = leaves.setdefault(
                holiday.holiday_status_id,
                {
                    "name": holiday.holiday_status_id.name or _("Global Leaves"),
                    "sequence": 5,
                    "code": holiday.holiday_status_id.code or "GLOBAL",
                    "number_of_days": 0.0,
                    "number_of_hours": 0.0,
                    "contract_id": contract.id,
                },
            )
            if leaves_positive:
                current_leave_struct["number_of_hours"] += hours
            else:
                current_leave_struct["number_of_hours"] -= hours
            work_hours = calendar.get_work_hours_count(
                tz.localize(datetime.combine(day, time.min)),
                tz.localize(datetime.combine(day, time.max)),
                compute_leaves=False,
            )
            if work_hours:
                if leaves_positive:
                    current_leave_struct["number_of_days"] += hours / work_hours
                else:
                    current_leave_struct["number_of_days"] -= hours / work_hours
        return leaves.values()

    def _compute_worked_days(self, contract, day_from, day_to):
        """
        Worked days computation
        @return: returns a list containing the total worked_days for the period
        of the payslip. This returns the FULL work days expected for the resource
        calendar selected for the employee (it don't substract leaves by default).
        """
        work_data = contract.employee_id._get_work_days_data_batch(
            day_from,
            day_to,
            calendar=contract.resource_calendar_id,
            compute_leaves=False,
        )
        return {
            "name": _("Normal Working Days paid at 100%"),
            "sequence": 1,
            "code": "WORK100",
            "number_of_days": work_data[contract.employee_id.id]["days"],
            "number_of_hours": work_data[contract.employee_id.id]["hours"],
            "contract_id": contract.id,
        }

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        # TODO: We leave date_from and date_to params here for backwards
        # compatibility reasons for the ones who inherit this function
        # in another modules, but they are not used.
        # Will be removed in next versions.
        """
        Inputs computation.
        @returns: Returns a dict with the inputs that are fetched from the salary_structure
        associated rules for the given contracts.
        """  # noqa: E501
        res = []
        current_structure = self.struct_id
        structure_ids = contracts.get_all_structures()
        if current_structure:
            structure_ids = list(set(current_structure._get_parent_structure().ids))
        rule_ids = (
            self.env["hr.payroll.structure"].browse(structure_ids).get_all_rules()
        )
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
        payslip_inputs = (
            self.env["hr.salary.rule"].browse(sorted_rule_ids).mapped("input_ids")
        )
        for contract in contracts:
            for payslip_input in payslip_inputs:
                res.append(
                    {
                        "name": payslip_input.name,
                        "code": payslip_input.code,
                        "contract_id": contract.id,
                    }
                )
        return res

    def _init_payroll_dict_contracts(self):
        return {
            "count": 0,
        }

    def get_payroll_dict(self, contracts):
        """Setup miscellaneous dictionary values.
        Other modules may overload this method to inject discreet values into
        the salary rules. Such values will be available to the salary rule
        under the `payroll.` prefix.

        This method is evaluated once per payslip.
        :param contracts: Recordset of all hr.contract records in this payslip
        :return: a dictionary of discreet values and/or Browsable Objects
        """
        self.ensure_one()

        res = {
            # In salary rules refer to this as: payroll.contracts.count
            "contracts": BaseBrowsableObject(self._init_payroll_dict_contracts()),
        }
        res["contracts"].count = len(contracts)

        return res

    def get_current_contract_dict(self, contract, contracts):
        """Contract dependent dictionary values.
        This method is called just before the salary rules are evaluated for
        contract.

        This method is evaluated once for every contract in the payslip.

        :param contract: The current hr.contract being processed
        :param contracts: Recordset of all hr.contract records in this payslip
        :return: a dictionary of discreet values and/or Browsable Objects
        """
        self.ensure_one()

        # res = super().get_current_contract_dict(contract, contracts)
        # res.update({
        #     # In salary rules refer to these as:
        #     #     current_contract.foo
        #     #     current_contract.foo.bar.baz
        #     "foo": 0,
        #     "bar": BaseBrowsableObject(
        #         {
        #             "baz": 0
        #         }
        #     )
        # })
        # <do something to update values in res>
        # return res

        return {}

    def _get_tools_dict(self):
        # _get_tools_dict() is intended to be inherited by other private modules
        # to add tools or python libraries available in localdict
        return {"math": math}  # "math" object is useful for doing calculations

    def _get_baselocaldict(self, contracts):
        self.ensure_one()
        worked_days_dict = {
            line.code: line for line in self.worked_days_line_ids if line.code
        }
        input_lines_dict = {
            line.code: line for line in self.input_line_ids if line.code
        }
        localdict = {
            "payslips": Payslips(self.employee_id.id, self, self.env),
            "worked_days": WorkedDays(self.employee_id.id, worked_days_dict, self.env),
            "inputs": InputLine(self.employee_id.id, input_lines_dict, self.env),
            "payroll": BrowsableObject(
                self.employee_id.id, self.get_payroll_dict(contracts), self.env
            ),
            "current_contract": BrowsableObject(self.employee_id.id, {}, self.env),
            "categories": BrowsableObject(self.employee_id.id, {}, self.env),
            "rules": BrowsableObject(self.employee_id.id, {}, self.env),
            "result_rules": BrowsableObject(self.employee_id.id, {}, self.env),
            "tools": BrowsableObject(
                self.employee_id.id, self._get_tools_dict(), self.env
            ),
        }
        return localdict

    def _get_salary_rules(self):
        rule_obj = self.env["hr.salary.rule"]
        sorted_rules = rule_obj
        for payslip in self:
            contracts = payslip._get_employee_contracts()
            if len(contracts) == 1 and payslip.struct_id:
                structure_ids = list(set(payslip.struct_id._get_parent_structure().ids))
            else:
                structure_ids = contracts.get_all_structures()
            rule_ids = (
                self.env["hr.payroll.structure"].browse(structure_ids).get_all_rules()
            )
            sorted_rule_ids = [
                id for id, sequence in sorted(rule_ids, key=lambda x: x[1])
            ]
            sorted_rules |= rule_obj.browse(sorted_rule_ids)
        return sorted_rules

    def _compute_payslip_line(self, rule, localdict, lines_dict):
        self.ensure_one()
        # check if there is already a rule computed with that code
        previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
        # compute the rule to get some values for the payslip line
        values = rule._compute_rule(localdict)
        key = (rule.code or "id" + str(rule.id)) + "-" + str(localdict["contract"].id)
        return self._get_lines_dict(
            rule, localdict, lines_dict, key, values, previous_amount
        )

    def _get_lines_dict(
        self, rule, localdict, lines_dict, key, values, previous_amount
    ):
        total = values["quantity"] * values["rate"] * values["amount"] / 100.0
        values["total"] = total
        # set/overwrite the amount computed for this rule in the localdict
        if rule.code:
            localdict[rule.code] = total
            localdict["rules"].dict[rule.code] = rule
            localdict["result_rules"].dict[rule.code] = BaseBrowsableObject(values)
        # sum the amount for its salary category
        localdict = self._sum_salary_rule_category(
            localdict, rule.category_id, total - previous_amount
        )
        # create/overwrite the line in the temporary results
        line_dict = {
            "salary_rule_id": rule.id,
            "employee_id": localdict["employee"].id,
            "contract_id": localdict["contract"].id,
            "code": rule.code,
            "category_id": rule.category_id.id,
            "sequence": rule.sequence,
            "appears_on_payslip": rule.appears_on_payslip,
            "parent_rule_id": rule.parent_rule_id.id,
            "condition_select": rule.condition_select,
            "condition_python": rule.condition_python,
            "condition_range": rule.condition_range,
            "condition_range_min": rule.condition_range_min,
            "condition_range_max": rule.condition_range_max,
            "amount_select": rule.amount_select,
            "amount_fix": rule.amount_fix,
            "amount_python_compute": rule.amount_python_compute,
            "amount_percentage": rule.amount_percentage,
            "amount_percentage_base": rule.amount_percentage_base,
            "register_id": rule.register_id.id,
        }
        line_dict.update(values)
        lines_dict[key] = line_dict
        return localdict, lines_dict

    @api.model
    def _get_payslip_lines(self, _contract_ids, payslip_id):
        _logger.warning(
            "Use of _get_payslip_lines() is deprecated. "
            "Use get_lines_dict() instead."
        )
        return self.browse(payslip_id).get_lines_dict()

    def get_lines_dict(self):
        lines_dict = {}
        blacklist = []
        for payslip in self:
            contracts = payslip._get_employee_contracts()
            baselocaldict = payslip._get_baselocaldict(contracts)
            for contract in contracts:
                # assign "current_contract" dict
                baselocaldict["current_contract"] = BrowsableObject(
                    payslip.employee_id.id,
                    payslip.get_current_contract_dict(contract, contracts),
                    payslip.env,
                )
                # set up localdict with current contract and employee values
                localdict = dict(
                    baselocaldict,
                    employee=contract.employee_id,
                    contract=contract,
                    payslip=payslip,
                )
                for rule in payslip._get_salary_rules():
                    localdict = rule._reset_localdict_values(localdict)
                    # check if the rule can be applied
                    if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                        localdict, _dict = payslip._compute_payslip_line(
                            rule, localdict, lines_dict
                        )
                        lines_dict.update(_dict)
                    else:
                        # blacklist this rule and its children
                        blacklist += [
                            id for id, seq in rule._recursive_search_of_rules()
                        ]
                # call localdict_hook
                localdict = payslip.localdict_hook(localdict)
                # reset "current_contract" dict
                baselocaldict["current_contract"] = {}
        return lines_dict

    def localdict_hook(self, localdict):
        # This hook is called when the function _get_lines_dict ends the loop
        # and before its returns. This method by itself don't add any functionality
        # and is intedend to be inherited to access localdict from other functions.
        return localdict

    def get_payslip_vals(
        self, date_from, date_to, employee_id=False, contract_id=False, struct_id=False
    ):
        # Initial default values for generated payslips
        employee = self.env["hr.employee"].browse(employee_id)
        res = {
            "value": {
                "line_ids": [],
                "input_line_ids": [(2, x) for x in self.input_line_ids.ids],
                "worked_days_line_ids": [(2, x) for x in self.worked_days_line_ids.ids],
                "name": "",
                "contract_id": False,
                "struct_id": False,
            }
        }
        # If we don't have employee or date data, we return.
        if (not employee_id) or (not date_from) or (not date_to):
            return res
        # We check if contract_id is present, if not we fill with the
        # first contract of the employee. If not contract present, we return.
        if not self.env.context.get("contract"):
            contract_ids = employee.contract_id.ids
        else:
            if contract_id:
                contract_ids = [contract_id]
            else:
                contract_ids = employee._get_contracts(
                    date_from=date_from, date_to=date_to
                ).ids
        if not contract_ids:
            return res
        contract = self.env["hr.contract"].browse(contract_ids[0])
        res["value"].update({"contract_id": contract.id})
        # We check if struct_id is already filled, otherwise we assign the contract struct. # noqa: E501
        # If contract don't have a struct, we return.
        if struct_id:
            res["value"].update({"struct_id": struct_id[0]})
        else:
            struct = contract.struct_id
            if not struct:
                return res
            res["value"].update({"struct_id": struct.id})
        # Computation of the salary input and worked_day_lines
        contracts = self.env["hr.contract"].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        res["value"].update(
            {
                "worked_days_line_ids": worked_days_line_ids,
                "input_line_ids": input_line_ids,
            }
        )
        return res

    def _sum_salary_rule_category(self, localdict, category, amount):
        self.ensure_one()
        if category.parent_id:
            localdict = self._sum_salary_rule_category(
                localdict, category.parent_id, amount
            )
        if category.code:
            localdict["categories"].dict[category.code] = (
                localdict["categories"].dict.get(category.code, 0) + amount
            )
        return localdict

    def _get_employee_contracts(self):
        contracts = self.env["hr.contract"]
        for payslip in self:
            if payslip.contract_id.ids:
                contracts |= payslip.contract_id
            else:
                contracts |= payslip.employee_id._get_contracts(
                    date_from=payslip.date_from, date_to=payslip.date_to
                )
        return contracts

    @api.onchange("struct_id")
    def onchange_struct_id(self):
        for payslip in self:
            if not payslip.struct_id:
                payslip.input_line_ids.unlink()
                return
            input_lines = payslip.input_line_ids.browse([])
            input_line_ids = payslip.get_inputs(
                payslip._get_employee_contracts(), payslip.date_from, payslip.date_to
            )
            for r in input_line_ids:
                input_lines += input_lines.new(r)
            payslip.input_line_ids = input_lines

    @api.onchange("date_from", "date_to")
    def onchange_dates(self):
        for payslip in self:
            if not payslip.date_from or not payslip.date_to:
                return
            worked_days_lines = payslip.worked_days_line_ids.browse([])
            worked_days_line_ids = payslip.get_worked_day_lines(
                payslip._get_employee_contracts(), payslip.date_from, payslip.date_to
            )
            for line in worked_days_line_ids:
                worked_days_lines += worked_days_lines.new(line)
            payslip.worked_days_line_ids = worked_days_lines

    @api.onchange("employee_id", "date_from", "date_to")
    def onchange_employee(self):
        for payslip in self:
            # Return if required values are not present.
            if (
                (not payslip.employee_id)
                or (not payslip.date_from)
                or (not payslip.date_to)
            ):
                continue
            # Assign contract_id automatically when the user don't selected one.
            if not payslip.env.context.get("contract") or not payslip.contract_id:
                contract_ids = payslip._get_employee_contracts().ids
                if not contract_ids:
                    continue
                payslip.contract_id = payslip.env["hr.contract"].browse(contract_ids[0])
            # Assign struct_id automatically when the user don't selected one.
            if not payslip.struct_id and not payslip.env.context.get("struct_id"):
                if not payslip.contract_id.struct_id:
                    continue
                payslip.struct_id = payslip.contract_id.struct_id
            # Compute payslip name
            payslip._compute_name()
            # Call worked_days_lines computation when employee is changed.
            payslip.onchange_dates()
            # Call input_lines computation when employee is changed.
            payslip.onchange_struct_id()
            # Assign company_id automatically based on employee selected.
            payslip.company_id = payslip.employee_id.company_id

    def _compute_name(self):
        for record in self:
            record.name = _("Salary Slip of %(name)s for %(dt)s") % {
                "name": record.employee_id.name,
                "dt": tools.ustr(
                    babel.dates.format_date(
                        date=datetime.combine(record.date_from, time.min),
                        format="MMMM-y",
                        locale=record.env.context.get("lang") or "en_US",
                    )
                ),
            }

    @api.onchange("contract_id")
    def onchange_contract(self):
        if not self.contract_id:
            self.struct_id = False
        self.with_context(contract=True).onchange_employee()
        return

    def get_salary_line_total(self, code):
        self.ensure_one()
        line = self.line_ids.filtered(lambda line: line.code == code)
        if line:
            return line[0].total
        else:
            return 0.0
