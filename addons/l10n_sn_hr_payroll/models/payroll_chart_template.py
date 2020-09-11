# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo import api, fields, models, _


class PayrollChartTemplate(models.Model):
    _name = "payroll.chart.template"
    _description = "Payroll Chart Template"

    name = fields.Char('Name')

    def load_for_current_company(self):
        """ Installs payroll salary rules on the current company, replacing
            the existing one if it had already one defined.

            Also, note that this function can only be run by someone with administration
            rights.
        """
        self.ensure_one()
        company = self.env.company
        # Ensure everything is translated to the company's language, not the user's one.
        self = self.with_context(lang=company.partner_id.lang)
        if not self.env.user._is_admin():
            raise AccessError(_("Only administrators can load a chart of accounts"))

        if company.id == 1:
            raise UserError(_('Can not change salary for My Company'))
            
        # delete existing salary rule
        for rule in self.env['hr.salary.rule'].search([('company_id', '=', company.id)]):
            rule.unlink()
            
        # delete existing salary rules category
        for rule_category in self.env['hr.salary.rule.category'].sudo().search([('company_id', '=', company.id)]):
            rule_category.unlink()
            
        # delete existing payroll structure type
        for rule in self.env['hr.payroll.structure'].search([('company_id', '=', company.id)]):
            rule.unlink()
            
        # delete existing payroll structure type
        for rule in self.env['hr.payroll.structure.type'].search([('company_id', '=', company.id)]):
            rule.unlink()
            

        # create salary rule and category
        self._create_salary_rule_category(company)
        # create salary rules
        self._create_salary_rule(company)

        return {}

    def _create_salary_rule_category(self, company):
        self.ensure_one()
        rules_category = self.env['hr.salary.rule.category']
        for salary_rule_category in self.env['hr.salary.rule.category'].sudo().search([('company_id', '=', 1)]):

            category = [c for c in self.env['hr.salary.rule.category'].sudo().search(
                    [('company_id', '=', company.id), ('code', '=', salary_rule_category.code)])]

            rules_category += self.env['hr.salary.rule.category'].create({
                'name': salary_rule_category.name,
                'code': salary_rule_category.code,
                'parent_id': category[0].id if len(category) > 0 else False,
                'company_id': company.id,
            })
        return rules_category

    def _create_salary_rule(self, company):
        self.ensure_one()
        salary_rules = self.env['hr.salary.rule']
        payroll_structure = self.env['hr.payroll.structure']
        
        # create payroll structure type
        struct_type = self.env['hr.payroll.structure.type'].create({
            'name': 'Employee SN',
            'company_id': company.id,
            'country_id': False
        })
        
        
        # create structure for salary rule
        payroll_structure = self.env['hr.payroll.structure'].create({
            'name': 'Worker Pay SN',
            'company_id': company.id,
            'type_id': struct_type.id,
        })

        # create salary rules
        for salary_rule in self.env['hr.salary.rule'].sudo().search([('company_id', '=', 1)]):
            # get the category
            category = [c for c in self.env['hr.salary.rule.category'].search(
                    [('company_id', '=', company.id), ('code', '=', salary_rule.category_id.code)])]

            rule_id = self.env['hr.salary.rule'].create({
                'name': salary_rule.name,
                'sequence': salary_rule.sequence,
                'code': salary_rule.code,
                'category_id': category[0].id,
                'condition_select': salary_rule.condition_select or False,
                'amount_select': salary_rule.amount_select or False,
                'amount_python_compute': salary_rule.amount_python_compute or False,
                'note': salary_rule.note or False,
                'appears_on_payslip': salary_rule.appears_on_payslip,
                'quantity': salary_rule.quantity,
                'amount_fix': salary_rule.amount_fix,
                'amount_percentage_base': salary_rule.amount_percentage_base or False,
                'condition_python': salary_rule.condition_python or False,
                'company_id': company.id,
                'struct_id': payroll_structure.id
            })

        # create rule input for the current salary rule in loop
        for rule_input in self.env['hr.payslip.input.type'].sudo().search([('company_id', '=', 1)]):
            self.env['hr.rule.input'].create({
                'name': rule_input.name,
                'code': rule_input.code,
                'company_id': company.id,
            })

        company.write({'payroll_chart_template': self.id})
        return payroll_structure



class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    payroll_chart_template = fields.Many2one(related='company_id.payroll_chart_template', string='Payroll Template', readonly=False)

    def set_values(self):
        """ install a chart of accounts for the given company (if required) """
        if self.payroll_chart_template and self.env.company.payroll_chart_template.id != self.payroll_chart_template.id:
            self.payroll_chart_template.load_for_current_company()
        super(ResConfigSettingsInherit, self).set_values()


class ResCompanyInherit(models.Model):
    _inherit = "res.company"

    payroll_chart_template = fields.Many2one('payroll.chart.template')
