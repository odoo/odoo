# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.safe_eval import safe_eval

from odoo import api, fields, models, _
from odoo.tools import ormcache
from odoo.tools.misc import format_date
from odoo.exceptions import UserError


class HrSalaryRuleParameterValue(models.Model):
    _name = 'hr.rule.parameter.value'
    _description = 'Salary Rule Parameter Value'
    _order = 'date_from desc'

    rule_parameter_id = fields.Many2one('hr.rule.parameter', required=True, ondelete='cascade', default=lambda self: self.env.context.get('active_id'))
    rule_parameter_name = fields.Char(related="rule_parameter_id.name", readonly=True)
    code = fields.Char(related="rule_parameter_id.code", index=True, store=True, readonly=True)
    date_from = fields.Date(string="From", index=True, required=True)
    parameter_value = fields.Text(help="Python data structure")
    country_id = fields.Many2one(related="rule_parameter_id.country_id")

    _sql_constraints = [
        ('_unique', 'unique (rule_parameter_id, date_from)', "Two rules with the same code cannot start the same day"),
    ]

    @api.constrains('parameter_value')
    def _check_parameter_value(self):
        for value in self:
            try:
                safe_eval(value.parameter_value)
            except Exception as e:
                raise UserError(_('Wrong rule parameter value for %(rule_parameter_name)s at date %(date)s.\n%(error)s', rule_parameter_name=value.rule_parameter_name, date=format_date(self.env, value.date_from), error=str(e)))

    @api.model_create_multi
    def create(self, vals_list):
        self.env.registry.clear_cache()
        return super().create(vals_list)

    def write(self, vals):
        if 'date_from' in vals or 'parameter_value' in vals:
            self.env.registry.clear_cache()
        return super().write(vals)

    def unlink(self):
        self.env.registry.clear_cache()
        return super().unlink()


class HrSalaryRuleParameter(models.Model):
    _name = 'hr.rule.parameter'
    _description = 'Salary Rule Parameter'

    name = fields.Char(required=True)
    code = fields.Char(required=True, help="This code is used in salary rules to refer to this parameter.")
    description = fields.Html()
    country_id = fields.Many2one('res.country', string='Country', default=lambda self: self.env.company.country_id)
    parameter_version_ids = fields.One2many('hr.rule.parameter.value', 'rule_parameter_id', string='Versions')

    _sql_constraints = [
        ('_unique', 'unique (code)', "Two rule parameters cannot have the same code."),
    ]

    @api.model
    @ormcache('code', 'date', 'tuple(self.env.context.get("allowed_company_ids", []))')
    def _get_parameter_from_code(self, code, date=None, raise_if_not_found=True):
        if not date:
            date = fields.Date.today()
        # This should be quite fast as it uses a limit and fields are indexed
        # moreover the method is cached
        rule_parameter = self.env['hr.rule.parameter.value'].search([
            ('code', '=', code),
            ('date_from', '<=', date)], limit=1)
        if rule_parameter:
            return safe_eval(rule_parameter.parameter_value)
        if raise_if_not_found:
            raise UserError(_('No rule parameter with code "%(code)s" was found for %(date)s', code=code, date=date))
        else:
            return None
