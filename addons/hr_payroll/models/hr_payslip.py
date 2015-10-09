# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp

# Removed class One2manyMod2(fields.One2many).
# Since there is no need to pass domain separately.


class HrPayslip(models.Model):
    '''
    Pay Slip
    '''

    _name = 'hr.payslip'
    _description = 'Pay Slip'

    struct_id = fields.Many2one('hr.payroll.structure', 'Structure', readonly=True, states={'draft': [('readonly', False)]}, help='Defines the rules that have to be applied to this payslip, accordingly to the contract chosen. If you let empty the field contract, this field isn\'t mandatory anymore and thus the rules applied will be all the rules set on the structure of all contracts of the employee valid for the chosen period')
    name = fields.Char('Payslip Name', readonly=True, states={'draft': [('readonly', False)]})
    number = fields.Char('Reference', readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True, readonly=True, states={'draft': [('readonly', False)]})
    date_from = fields.Date(readonly=True, default=lambda *a: time.strftime('%Y-%m-01'), states={'draft': [('readonly', False)]}, required=True)
    date_to = fields.Date(readonly=True, default=lambda *a: fields.date.today() + relativedelta(months=+1, day=1, days=-1), states={'draft': [('readonly', False)]}, required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], 'Status', index=True, readonly=True, copy=False, default='draft',
        help='* When the payslip is created the status is \'Draft\'.\
            \n* If the payslip is under verification, the status is \'Waiting\'. \
            \n* If the payslip is confirmed then status is set to \'Done\'.\
            \n* When user cancel payslip the status is \'Rejected\'.')
    line_ids = fields.One2many('hr.payslip.line', 'slip_id', 'Payslip Lines', readonly=True, states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id, readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    worked_days_line_ids = fields.One2many('hr.payslip.worked_days', 'payslip_id', string='Payslip Worked Days', readonly=True, states={'draft': [('readonly', False)]})
    input_line_ids = fields.One2many('hr.payslip.input', 'payslip_id', 'Payslip Inputs', readonly=True, states={'draft': [('readonly', False)]})
    paid = fields.Boolean('Made Payment Order ? ', readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    note = fields.Text('Internal Note', readonly=True, states={'draft': [('readonly', False)]})
    contract_id = fields.Many2one('hr.contract', 'Contract', readonly=True, states={'draft': [('readonly', False)]})
    details_by_salary_rule_category = fields.One2many('hr.payslip.line', compute='_compute_details_by_salary_rule_category', string='Details by Salary Rule Category')
    credit_note = fields.Boolean(readonly=True, states={'draft': [('readonly', False)]}, help="Indicates this payslip has a refund of another")
    payslip_run_id = fields.Many2one('hr.payslip.run', 'Payslip Batches', readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    payslip_count = fields.Integer(compute='_compute_payslip_count', string='Payslip Computation Details')

    @api.constrains('date_from', 'date_to')
    def check_dates(self):
        if self.filtered(lambda x: x.date_from > x.date_to):
            raise ValidationError(
                _("Payslip 'Date From create must be before 'Date To'"))

    def _compute_payslip_count(self):
        payslip_data = self.env['hr.payslip.line'].read_group([('slip_id', 'in', self.ids)], ['slip_id'], ['slip_id'])
        mapped_data = dict([(m['slip_id'][0], m['slip_id_count']) for m in payslip_data])
        for payslip in self:
            payslip.payslip_count = mapped_data.get(payslip.id, 0)

    def _compute_details_by_salary_rule_category(self):
        listdata = []
        if self.ids:
            self.env.cr.execute('''SELECT pl.id FROM hr_payslip_line AS pl \
                        LEFT JOIN hr_salary_rule_category AS sh on (pl.category_id = sh.id) \
                        WHERE pl.slip_id in %s \
                        GROUP BY pl.slip_id, pl.sequence, pl.id ORDER BY pl.sequence''', (tuple(self.ids),))
            res = self.env.cr.fetchall()
            for r in res:
                listdata.append(r[0])
        self.details_by_salary_rule_category = [(6, 0, listdata)]

    @api.multi
    def cancel_sheet(self):
        return self.write({'state': 'cancel'})

    @api.multi
    def process_sheet(self):
        return self.write({'paid': True, 'state': 'done'})

    @api.multi
    def hr_verify_sheet(self):
        self.compute_sheet()
        return self.write({'state': 'verify'})

    @api.multi
    def refund_sheet(self):
        for payslip in self:
            payslip_copy = payslip.copy({'credit_note': True, 'name': _('Refund: %s') % payslip.name})
            payslip_copy.signal_workflow('hr_verify_sheet')
            payslip_copy.signal_workflow('process_sheet')

        form_res = self.env.ref('hr_payroll.view_hr_payslip_form', False)
        tree_res = self.env.ref('hr_payroll.view_hr_payslip_tree', False)
        return {
            'name': _("Refund Payslip"),
            'view_mode': 'tree, form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % [payslip_copy.id],
            'views': [(tree_res.id, 'tree'), (form_res.id, 'form')],
        }

    def check_done(self):
        return True

    @api.multi
    def unlink(self):
        for payslip in self.filtered(lambda x: x.state not in ['draft', 'cancel']):
            raise UserError(_('You cannot delete a payslip which is not draft or cancelled'))
        return super(HrPayslip, self).unlink()

    # TODO move this function into hr_contract module, on hr.employee object
    def get_contract(self, employee, date_from, date_to):
        """
        :param employee: browse record of employee
        :param date_from: date field
        :param date_to: date field
        :return: The contracts for the given employee that need to be considered for the given dates
        """
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', employee.id), '|', '|'] + clause_1 + clause_2 + clause_3
        return self.env['hr.contract'].search(clause_final)

    @api.multi
    def compute_sheet(self):
        IrSequence = self.env['ir.sequence']
        for payslip in self:
            number = payslip.number or IrSequence.next_by_code('salary.slip')
            # delete old payslip lines
            payslip.line_ids.unlink()
            # if we don't give the contract, then the rules to apply should be for all current contracts of the employee
            contracts = payslip.contract_id
            if not contracts:
                contracts = self.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)
            lines = [(0, 0, line) for line in payslip.get_payslip_lines(contracts)]
            payslip.write({'line_ids': lines, 'number': number})
        return True

    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        :param contracts: list of contracts
        :return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        def was_on_leave(employee_id, datetime_day):
            day = fields.Date.to_string(datetime_day)
            return self.env['hr.holidays'].search([('state', '=', 'validate'), ('employee_id', '=', employee_id), ('type', '=', 'remove'), ('date_from', '<=', day), ('date_to', '>=', day)], limit=1).holiday_status_id.name

        res = []
        ResourceCalender = self.env['resource.calendar']
        for contract in contracts.filtered(lambda x: x.working_hours):
            attendances = {
                 'name': _("Normal Working Days paid at 100%"),
                 'sequence': 1,
                 'code': 'WORK100',
                 'number_of_days': 0.0,
                 'number_of_hours': 0.0,
                 'contract_id': contract.id,
            }
            day_from = fields.Datetime.from_string(date_from)
            day_to = fields.Datetime.from_string(date_to)
            nb_of_days = (day_to - day_from).days + 1
            for day in range(0, nb_of_days):
                working_hours_on_day = ResourceCalender.working_hours_on_day(contract.working_hours, day_from + timedelta(days=day))
                if working_hours_on_day:
                    # the employee had to work
                    leave_type = was_on_leave(contract.employee_id.id, day_from + timedelta(days=day))
                    # add the input vals to tmp (increment if existing)
                    attendances['number_of_days'] += 1.0
                    attendances['number_of_hours'] += working_hours_on_day
                    if leave_type and leave_type not in attendances:
                        attendances = {
                            'name': leave_type,
                            'sequence': 5,
                            'code': leave_type,
                            'number_of_days': 1.0,
                            'number_of_hours': working_hours_on_day,
                            'contract_id': contract.id,
                        }
            res += [attendances]
        return res

    def get_inputs(self, contracts):
        res = []
        structure_ids = contracts.get_all_structures()
        rule_ids = structure_ids.get_all_rules()
        sorted_rules = [rule for rule, sequence in sorted(rule_ids, key=lambda x: x[1])]

        for contract in contracts:
            for rule in sorted_rules:
                for rule_input in rule.input_ids:
                    inputs = {
                        'name': rule_input.name,
                        'code': rule_input.code,
                        'contract_id': contract.id,
                    }
                    res += [inputs]
        return res

    def get_payslip_lines(self, contracts):

        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
            localdict['categories'].dict[category.code] = category.code in localdict['categories'].dict and localdict['categories'].dict[category.code] + amount or amount
            return localdict

        class BrowsableObject(object):
            def __init__(self, pool, cr, uid, employee_id, dict):
                self.pool = pool
                self.cr = cr
                self.uid = uid
                self.employee_id = employee_id
                self.dict = dict

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = datetime.now().strftime('%Y-%m-%d')
                self.cr.execute("SELECT sum(amount) as sum\
                            FROM hr_payslip as hp, hr_payslip_input as pi \
                            WHERE hp.employee_id = %s AND hp.state = 'done' \
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s", (self.employee_id, from_date, to_date, code))
                res = self.cr.fetchone()[0]
                return res or 0.0

        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = datetime.now().strftime('%Y-%m-%d')
                self.cr.execute("SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours\
                            FROM hr_payslip as hp, hr_payslip_worked_days as pi \
                            WHERE hp.employee_id = %s AND hp.state = 'done'\
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s", (self.employee_id, from_date, to_date, code))
                return self.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = datetime.now().strftime('%Y-%m-%d')
                self.cr.execute("SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)\
                            FROM hr_payslip as hp, hr_payslip_line as pl \
                            WHERE hp.employee_id = %s AND hp.state = 'done' \
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s", (self.employee_id, from_date, to_date, code))
                res = self.cr.fetchone()
                return res and res[0] or 0.0

        # we keep a dict with the result because a value can be overwritten by another rule with the same code
        result_dict = {}
        rules = {}
        categories_dict = {}
        blacklist = []
        payslip = self
        worked_days = {}
        for worked_days_line in payslip.worked_days_line_ids:
            worked_days[worked_days_line.code] = worked_days_line
        inputs = {}
        for input_line in payslip.input_line_ids:
            inputs[input_line.code] = input_line

        categories_obj = BrowsableObject(self.pool, self._cr, self._uid, payslip.employee_id.id, categories_dict)
        input_obj = InputLine(self.pool, self._cr, self._uid, payslip.employee_id.id, inputs)
        worked_days_obj = WorkedDays(self.pool, self._cr, self._uid, payslip.employee_id.id, worked_days)
        payslip_obj = Payslips(self.pool, self._cr, self._uid, payslip.employee_id.id, payslip)
        rules_obj = BrowsableObject(self.pool, self._cr, self._uid, payslip.employee_id.id, rules)

        baselocaldict = {'categories': categories_obj, 'rules': rules_obj, 'payslip': payslip_obj, 'worked_days': worked_days_obj, 'inputs': input_obj}
        # get the structures on the contracts and their parent id as well
        structure_ids = contracts.get_all_structures()
        # get the rules of the structure and thier children
        rule_ids = structure_ids.get_all_rules()
        # run the rules by sequence
        sorted_rules = [rule for rule, sequence in sorted(rule_ids, key=lambda x: x[1])]

        for contract in contracts:
            localdict = dict(baselocaldict, employee=contract.employee_id, contract=contract)
            for rule in sorted_rules:
                key = rule.code + '-' + str(contract.id)
                localdict['result'] = None
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100
                # check if the rule can be applied
                if rule.satisfy_condition(localdict) and rule.id not in blacklist:
                    # compute the amount of the rule
                    amount, qty, rate = rule.compute_rule(localdict)
                    # check if there is already a rule computed with that code
                    previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                    # set/overwrite the amount computed for this rule in the localdict
                    tot_rule = amount * qty * rate / 100.0
                    localdict[rule.code] = tot_rule
                    rules[rule.code] = rule
                    # sum the amount for its salary category
                    localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                    # create/overwrite the rule in the temporary results
                    result_dict[key] = {
                        'salary_rule_id': rule.id,
                        'contract_id': contract.id,
                        'name': rule.name,
                        'code': rule.code,
                        'category_id': rule.category_id.id,
                        'sequence': rule.sequence,
                        'appears_on_payslip': rule.appears_on_payslip,
                        'condition_select': rule.condition_select,
                        'condition_python': rule.condition_python,
                        'condition_range': rule.condition_range,
                        'condition_range_min': rule.condition_range_min,
                        'condition_range_max': rule.condition_range_max,
                        'amount_select': rule.amount_select,
                        'amount_fix': rule.amount_fix,
                        'amount_python_compute': rule.amount_python_compute,
                        'amount_percentage': rule.amount_percentage,
                        'amount_percentage_base': rule.amount_percentage_base,
                        'register_id': rule.register_id.id,
                        'amount': amount,
                        'employee_id': contract.employee_id.id,
                        'quantity': qty,
                        'rate': rate,
                    }
                else:
                    # blacklist this rule and its children
                    blacklist += [id for id, seq in rule._recursive_search_of_rules()]

        result = [value for code, value in result_dict.items()]
        return result

    @api.multi
    @api.onchange('employee_id', 'date_from')
    def onchange_employee_id_wrapper(self):
        self.ensure_one()
        values = self.onchange_employee_id(self.date_from, self.date_to, self.employee_id.id, self.contract_id.id)['value']
        for fname, value in values.iteritems():
            setattr(self, fname, value)

    @api.multi
    def onchange_employee_id(self, date_from, date_to, employee_id=False, contract_id=False):
        # delete old worked days lines
        self.worked_days_line_ids.unlink()
        # delete old input lines
        self.input_line_ids.unlink()

        # defaults
        res = {'value': {
                      'line_ids': [],
                      'input_line_ids': [],
                      'worked_days_line_ids': [],
                      # 'details_by_salary_head':[], TODO put me back
                      'name': '',
                      'contract_id': False,
                      'struct_id': False,
                    }}

        if (not employee_id) or (not date_from) or (not date_to):
            return res
        ttyme = datetime.fromtimestamp(time.mktime(time.strptime(date_from, "%Y-%m-%d")))
        employee = self.env['hr.employee'].browse(employee_id)
        res['value'].update({
                    'name': _('Salary Slip of %s for %s') % (employee.name, tools.ustr(ttyme.strftime('%B-%Y'))),
                    'company_id': employee.company_id.id
        })

        if not self.env.context.get('contract') or not contract_id:
            # fill with the first contract of the employee
            contracts = self.get_contract(employee, date_from, date_to)
        if contract_id:
            # set the list of contract for which the input have to be filled
            contracts = self.env['hr.contract'].browse(contract_id)
        if not contracts:
            return res
        contract = contracts[0]
        res['value'].update({
                    'contract_id': contract.id
        })
        struct_record = contract.struct_id
        if not struct_record:
            return res
        res['value'].update({
                    'struct_id': struct_record.id,
        })
        # computation of the salary input
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
        input_line_ids = self.get_inputs(contracts)
        res['value'].update({
            'worked_days_line_ids': worked_days_line_ids,
            'input_line_ids': input_line_ids,
        })
        return res

    @api.multi
    @api.onchange('contract_id')
    def onchange_contract_id_wrapper(self):
        self.ensure_one()
        values = self.onchange_contract_id(self.date_from, self.date_to, self.employee_id.id, self.contract_id.id)['value']
        for fname, value in values.iteritems():
            setattr(self, fname, value)

    @api.multi
    def onchange_contract_id(self, date_from, date_to, employee_id=False, contract_id=False):
        # TODO it seems to be the mess in the onchanges, we should have onchange_employee => onchange_contract => doing all the things
        return self.with_context(contract=True).onchange_employee_id(date_from=date_from, date_to=date_to, employee_id=employee_id, contract_id=contract_id)

    @api.onchange('employee_id', 'date_from')
    def onchange_employee(self):

        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return

        employee_id = self.employee_id
        date_from = self.date_from
        date_to = self.date_to

        ttyme = datetime.fromtimestamp(time.mktime(time.strptime(date_from, "%Y-%m-%d")))
        self.name = _('Salary Slip of %s for %s') % (employee_id.name, tools.ustr(ttyme.strftime('%B-%Y')))
        self.company_id = employee_id.company_id

        if not self.env.context.get('contract') or not self.contract_id:
            contract_ids = self.get_contract(employee_id, date_from, date_to)
            if not contract_ids:
                return
            self.contract_id = self.contract_id.browse(contract_ids[0].id)

        if not self.contract_id.struct_id:
            return
        self.struct_id = self.contract_id.struct_id

        # computation of the salary input
        worked_days_line_ids = self.get_worked_day_lines(contract_ids, date_from, date_to)
        worked_days_lines = self.worked_days_line_ids.browse([])
        for r in worked_days_line_ids:
            worked_days_lines += worked_days_lines.new(r)
        self.worked_days_line_ids = worked_days_lines

        input_line_ids = self.get_inputs(contract_ids)
        input_lines = self.input_line_ids.browse([])
        for line in input_line_ids:
            input_lines += input_lines.new(line)
        self.input_line_ids = input_lines
        return

    @api.onchange('contract_id')
    def onchange_contract(self):
        if not self.contract_id:
            self.struct_id = False
        self.with_context(contract=True).onchange_employee()
        return

class HrPayslipLine(models.Model):
    '''
    Payslip Line
    '''

    _name = 'hr.payslip.line'
    _inherit = 'hr.salary.rule'
    _description = 'Payslip Line'
    _order = 'contract_id, sequence'

    slip_id = fields.Many2one('hr.payslip', 'Pay Slip', required=True, ondelete='cascade')
    salary_rule_id = fields.Many2one('hr.salary.rule', 'Rule', required=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    contract_id = fields.Many2one('hr.contract', 'Contract', required=True, index=True)
    rate = fields.Float('Rate (%)', digits=dp.get_precision('Payroll Rate'), default=100.0)
    amount = fields.Float(digits=dp.get_precision('Payroll'))
    quantity = fields.Float(digits=dp.get_precision('Payroll'), default=1.0)
    total = fields.Float(compute='_compute_total', digits=dp.get_precision('Payroll'), store=True)

    @api.depends('quantity', 'amount', 'rate')
    def _compute_total(self):
        for line in self:
            line.total = float(line.quantity) * line.amount * line.rate / 100


class HrPayslipWorkedDays(models.Model):
    '''
    Payslip Worked Days
    '''

    _name = 'hr.payslip.worked_days'
    _description = 'Payslip Worked Days'
    _order = 'payslip_id, sequence'

    name = fields.Char('Description', required=True)
    payslip_id = fields.Many2one('hr.payslip', 'Pay Slip', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    code = fields.Char(size=52, required=True, help="The code that can be used in the salary rules")
    number_of_days = fields.Float()
    number_of_hours = fields.Float()
    contract_id = fields.Many2one('hr.contract', 'Contract', required=True, help="The contract for which applied this input")


class HrPayslipInput(models.Model):
    '''
    Payslip Input
    '''

    _name = 'hr.payslip.input'
    _description = 'Payslip Input'
    _order = 'payslip_id, sequence'

    name = fields.Char('Description', required=True)
    payslip_id = fields.Many2one('hr.payslip', 'Pay Slip', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    code = fields.Char(size=52, required=True, help="The code that can be used in the salary rules")
    amount = fields.Float(default=0.0, help="It is used in computation. For e.g. A rule for sales having 1% commission of basic salary for per product can defined in expression like result = inputs.SALEURO.amount * contract.wage*0.01.")
    contract_id = fields.Many2one('hr.contract', 'Contract', required=True, help="The contract for which applied this input")


class HrPayslipRun(models.Model):

    _name = 'hr.payslip.run'
    _description = 'Payslip Batches'

    name = fields.Char(required=True, readonly=True, states={'draft': [('readonly', False)]})
    slip_ids = fields.One2many('hr.payslip', 'payslip_run_id', 'Payslips', readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('close', 'Close'),
    ], 'Status', index=True, readonly=True, copy=False, default='draft')
    date_start = fields.Date('Date From', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda *a: time.strftime('%Y-%m-01'))
    date_end = fields.Date('Date To', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda *a: str(datetime.now() + relativedelta(months=+1, day=1, days=-1))[:10])
    credit_note = fields.Boolean(readonly=True, states={'draft': [('readonly', False)]}, help="If its checked, indicates that all payslips generated from here are refund payslips.")

    @api.multi
    def draft_payslip_run(self):
        return self.write({'state': 'draft'})

    @api.multi
    def close_payslip_run(self):
        return self.write({'state': 'close'})
