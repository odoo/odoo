# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models, api, fields, _
from odoo.tools import html2plaintext
from odoo.exceptions import ValidationError


ACTIONS = [
    ('trim', _('Trim Spaces')),
    ('case', _('Set Type Case')),
    ('phone', _('Format Phone')),
    ('html', _('Scrap HTML')),
]

ACTIONS_TRIM = [
    ('all', _('All Spaces')),
    ('superfluous', _('Superfluous Spaces')),
]

ACTIONS_CASE = [
    ('first', _('First Letters to Uppercase')),
    ('upper', _('All Uppercase')),
    ('lower', _('All Lowercase')),
]

ACTIONS_PYTHON = {
    'trim_all': lambda record, value: value.replace(' ', ''),
    'trim_superfluous': lambda record, value: re.sub(r'\s+', ' ', value.strip()),
    'case_first': lambda record, value: value.title(),
    'case_upper': lambda record, value: value.upper(),
    'case_lower': lambda record, value: value.lower(),
    'phone': lambda record, value: record._phone_format(number=value, country=record.country_id, force_format="INTERNATIONAL"),
    'html': lambda record, value: html2plaintext(value),
}

ACTIONS_SQL = {
    'trim_all': ('<>', "REPLACE({}, ' ', '')"),
    'trim_superfluous': ('<>', r"TRIM(REGEXP_REPLACE({}, '\s+', ' ', 'g'))"),
    'case_first': ('<>', 'INITCAP({})'),
    'case_upper': ('<>', 'UPPER({})'),
    'case_lower': ('<>', 'LOWER({})'),
    'phone': (False, 'format_phone'),  # special case, needs to be treated in Python
    'html': ('~', "'<[a-z]+.*>'"),
}


class DataCleaningRule(models.Model):
    _name = 'data_cleaning.rule'
    _description = 'Cleaning Rule'
    _order = 'sequence'

    name = fields.Char(related='field_id.name')
    cleaning_model_id = fields.Many2one(
        'data_cleaning.model', string='Cleaning Model', required=True, ondelete='cascade')
    res_model_id = fields.Many2one(
        related='cleaning_model_id.res_model_id', readonly=True, store=True)
    res_model_name = fields.Char(
        related='cleaning_model_id.res_model_name', string='Model Name', readonly=True, store=True)
    field_id = fields.Many2one(
        'ir.model.fields', string='Field',
        domain="[('model_id', '=', res_model_id), ('ttype', 'in', ('char', 'text', 'html')), ('store', '=', True)]",
        required=True, ondelete='cascade')

    action = fields.Selection(ACTIONS, string='Action', default='trim', required=True)
    action_trim = fields.Selection(
        ACTIONS_TRIM, string='Trim', default='all',
        help="Which spaces are trimmed by the rule. Leading, trailing, and successive spaces are considered superfluous.")
    action_case = fields.Selection(
        ACTIONS_CASE, string='Case', default='first',
        help="How the type case is set by the rule. 'First Letters to Uppercase' sets every letter to lowercase except the first letter of each word, which is set to uppercase.")
    action_technical = fields.Char(compute='_compute_action')
    action_display = fields.Char(compute='_compute_action')

    sequence = fields.Integer(string='Sequence', default=1)

    @api.depends('action', 'action_trim', 'action_case')
    def _compute_action(self):
        for rule in self:
            action = rule.action
            action_display = dict(ACTIONS).get(action, '')
            if action == 'trim':
                action = '%s_%s' % (action, rule.action_trim)
                action_display = '%s (%s)' % (action_display, dict(ACTIONS_TRIM).get(rule.action_trim))
            elif action == 'case':
                action = '%s_%s' % (action, rule.action_case)
                action_display = '%s (%s)' % (action_display, dict(ACTIONS_CASE).get(rule.action_case))
            rule.action_technical = action
            rule.action_display = action_display

    def _action_to_sql(self):
        field_actions = {}
        for rule in self:
            existing_action = field_actions.get(rule.name, {}).get('action', '{}')
            if field_actions.get(rule.name, {}).get('special_case'):
                continue

            operator, action = ACTIONS_SQL.get(rule.action_technical)
            if not operator or operator != '<>':
                field_actions[rule.name] = dict(action=action, rule_ids=rule.ids, field_id=rule.field_id.id, operator=operator, special_case=True)
            else:
                field_actions.setdefault(rule.name, dict(rule_ids=[], field_id=rule.field_id.id, operator=operator))
                field_actions[rule.name]['rule_ids'].append(rule.id)
                field_actions[rule.name]['action'] = action.format(existing_action)
        return field_actions

    def _action_to_python(self):
        self.ensure_one()
        return ACTIONS_PYTHON.get(self.action_technical)

    @api.onchange('action')
    def _onchange_action(self):
        if self.action == 'phone':
            try:
                import phonenumbers
            except ModuleNotFoundError:
                raise ValidationError(_('The Python module `phonenumbers` is not installed. Format phone will not work.'))
