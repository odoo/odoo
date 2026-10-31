import logging
from types import SimpleNamespace

from odoo import models
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class CustomPayrollRuleEngine(models.AbstractModel):
    _name = 'custom.payroll.rule.engine'
    _description = 'Salary Rule Engine (helper for executing Python rules)'

    def _build_categories(self, payslip):
        bpjs_total = sum(
            payslip.detail_ids.filtered(lambda d: d.component_type == 'bpjs').mapped('nominal')
        )
        return SimpleNamespace(
            BASIC=payslip.total_gaji_pokok,
            TUNJANGAN=payslip.total_tunjangan,
            LEMBUR=payslip.total_lembur,
            POTONGAN=payslip.total_potongan - bpjs_total,
            BPJS=bpjs_total,
            NET=payslip.total_pendapatan,
        )

    def _build_localdict(self, payslip):
        return {
            'employee': payslip.employee_id,
            'contract': payslip.employee_id.version_id if payslip.employee_id else None,
            'payslip': payslip,
            'categories': self._build_categories(payslip),
            'result': 0.0,
            'True': True,
            'False': False,
            'None': None,
            'round': round,
            'abs': abs,
            'min': min,
            'max': max,
            'sum': sum,
        }

    def _eval_condition(self, rule, localdict):
        if rule.condition_mode == 'simple':
            # Keep legacy Python conditions working when an existing rule is upgraded.
            if rule.condition_type == 'always' and (rule.condition or 'True').strip() not in ('', 'True'):
                return self._eval_python_condition(rule.condition, localdict)
            return self._eval_simple_condition(rule, localdict)
        return self._eval_python_condition(rule.condition, localdict)

    def _eval_python_condition(self, expr, localdict):
        try:
            return bool(safe_eval(expr, localdict, mode='eval'))
        except Exception as e:
            _logger.warning('Rule condition eval failed: %s | expr=%s', e, expr)
            return False

    def _eval_simple_condition(self, rule, localdict):
        condition_type = rule.condition_type or 'always'
        if condition_type == 'always':
            return True

        employee = localdict['employee']
        categories = localdict['categories']
        if condition_type == 'department':
            actual = employee.department_id
            expected = rule.condition_department_id
        elif condition_type == 'job':
            actual = employee.job_id
            expected = rule.condition_job_id
        elif condition_type == 'active':
            actual = employee.active
            expected = rule.condition_value_bool
        elif condition_type == 'basic_salary':
            actual = categories.BASIC
            expected = rule.condition_value_float
        elif condition_type == 'contract_wage':
            contract = localdict['contract']
            actual = getattr(contract, 'contract_wage', 0.0) if contract else 0.0
            expected = rule.condition_value_float
        elif condition_type == 'payroll_month':
            actual = localdict['payslip'].payroll_batch_id.periode_bulan
            expected = rule.condition_month
        elif condition_type == 'category':
            actual = getattr(categories, rule.condition_category)
            expected = rule.condition_value_float
        else:
            _logger.warning('Unknown simple condition type: %s', condition_type)
            return False

        return self._compare(actual, rule.condition_operator or '=', expected)

    def _compare(self, actual, operator, expected):
        if operator == '=':
            return actual == expected
        if operator == '!=':
            return actual != expected
        if operator == '>':
            return actual > expected
        if operator == '>=':
            return actual >= expected
        if operator == '<':
            return actual < expected
        if operator == '<=':
            return actual <= expected
        _logger.warning('Unknown condition operator: %s', operator)
        return False

    def _eval_amount(self, rule, localdict):
        if rule.amount_mode == 'fixed':
            # Existing installations receive the new field with its default value.
            # Keep their non-default Python amount until the rule is edited.
            if rule.amount_value == 0.0 and (rule.amount_python or '').strip() not in ('', 'result = 0.0'):
                return self._eval_python_amount(rule.amount_python, localdict)
            return rule.amount_value

        if rule.amount_mode == 'percentage':
            base = self._amount_base(rule.amount_base, localdict)
            return base * rule.amount_value / 100.0

        return self._eval_python_amount(rule.amount_python, localdict)

    def _amount_base(self, base_name, localdict):
        payslip = localdict['payslip']
        categories = localdict['categories']
        if base_name == 'basic_salary':
            return categories.BASIC
        if base_name == 'contract_wage':
            contract = localdict['contract']
            return getattr(contract, 'contract_wage', 0.0) if contract else 0.0
        if base_name == 'gross':
            return payslip.total_earnings
        if base_name == 'net':
            return categories.NET
        if base_name == 'allowance':
            return categories.TUNJANGAN
        if base_name == 'overtime':
            return categories.LEMBUR
        if base_name == 'bpjs':
            return categories.BPJS
        raise ValueError('Unknown computation base: {}'.format(base_name))

    def _eval_python_amount(self, code, localdict):
        safe_eval(code or 'result = 0.0', localdict, mode='exec')
        return localdict.get('result', 0.0)

    def run_rules(self, payslip, raise_on_error=False):
        rules = self.env['custom.payroll.rule'].search([
            ('company_id', '=', payslip.company_id.id),
            ('active', '=', True),
        ], order='sequence, id')
        results = []
        for rule in rules:
            localdict = self._build_localdict(payslip)
            try:
                if self._eval_condition(rule, localdict):
                    amount = float(self._eval_amount(rule, localdict) or 0.0)
                else:
                    amount = 0.0
            except Exception as e:
                _logger.error('Rule %s execution failed: %s', rule.code, e)
                if raise_on_error:
                    raise
                amount = 0.0
            results.append((rule, amount))
        return results
