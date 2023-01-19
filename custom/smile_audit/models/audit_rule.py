# -*- coding: utf-8 -*-
# (C) 2021 Smile (<https://www.smile.eu>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import api, fields, models, tools, _

from ..tools import audit_decorator

_logger = logging.getLogger(__package__)


class AuditRule(models.Model):
    _name = 'audit.rule'
    _description = 'Audit Rule'

    name = fields.Char(size=32, required=True)
    active = fields.Boolean(default=True)
    log_create = fields.Boolean('Log Creation', default=False)
    log_write = fields.Boolean('Log Update', default=True)
    log_unlink = fields.Boolean('Log Deletion', default=True)
    group_id = fields.Many2one('res.groups', 'User Group')
    state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Done')], 'Status',
        default='draft', readonly=True)
    model_id = fields.Many2one(
        'ir.model', 'Model', required=True,
        help='Select model for which you want to generate log.',
        domain=[('model', '!=', 'audit.log')],
        readonly=True, states={'draft': [('readonly', False)]},
        ondelete='cascade')
    action_id = fields.Many2one(
        'ir.actions.act_window', "Add in the 'More' menu", readonly=True)

    _sql_constraints = [
        ('model_uniq', 'unique(model_id, group_id)',
         'There is already a rule defined on this model and this group.\n'
         'You cannot define another: please edit the existing one.'),
    ]

    def _add_action(self):
        if not self.action_id:
            vals = {
                'name': _('View audit logs'),
                'res_model': 'audit.log',
                'binding_model_id': self.model_id.id,
                'domain': "[('model_id','=', %s), "
                          "('res_id', '=', active_id), ('method', 'in', %s)]"
                          % (self.model_id.id, [method.replace('_', '')
                             for method in self._methods])
            }
            self.action_id = self.env['ir.actions.act_window'].create(vals)

    def _activate(self):
        if self._context and \
                self._context.get('activation_in_progress'):
            return
        self = self.with_context(activation_in_progress=True)
        self._add_action()

    def _deactivate(self):
        if self.action_id:
            self.action_id.unlink()

    def update_rule(self, force_deactivation=False):
        for rule in self:
            if rule.active and not force_deactivation:
                rule._activate()
            else:
                rule._deactivate()
        return True

    _methods = ['create', 'write', '_write', 'unlink']

    @api.model
    @tools.ormcache()
    def _check_audit_rule(self, group_ids):
        rules = self.sudo().search([
            '|',
            ('group_id', '=', False),
            ('group_id', 'in', group_ids),
        ])
        return {rule.model_id.model:
                {method.replace('_', ''): rule.id
                 for method in self._methods
                 if getattr(rule, 'log_%s' % method.replace('_', ''))}
                for rule in rules}

    @api.model
    def _register_hook(self, ids=None):
        self = self.sudo()
        updated = False
        if ids:
            rules = self.browse(ids)
        else:
            rules = self.search([])
        for rule in rules:
            if rule.model_id.model not in self.env.registry.models or \
                    not rule.active:
                continue
            RecordModel = self.env[rule.model_id.model]
            for method in self._methods:
                func = getattr(RecordModel, method)
                while hasattr(func, 'origin'):
                    if func.__name__.startswith('audit_'):
                        break
                    func = func.origin
                else:
                    RecordModel._patch_method(method, audit_decorator(method))
            updated = bool(ids)
        if updated:
            self.clear_caches()
        return updated

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        vals['state'] = 'done'
        rule = super(AuditRule, self).create(vals)
        rule.update_rule()
        if self._register_hook(rule.id):
            self.pool.signal_changes()
        return rule

    def write(self, vals):
        res = super(AuditRule, self).write(vals)
        self.update_rule()
        if self._register_hook(self._ids):
            self.pool.signal_changes()
        return res

    def unlink(self):
        self.update_rule(force_deactivation=True)
        return super(AuditRule, self).unlink()

    _ignored_fields = ['__last_update', 'message_ids', 'message_last_post']

    @classmethod
    def _format_data_to_log(cls, old_values, new_values):
        data = {}
        for age in ('old', 'new'):
            vals_list = old_values if age == 'old' else new_values
            if isinstance(vals_list, dict):
                vals_list = [vals_list]
            for vals in vals_list or []:
                for field in cls._ignored_fields:
                    vals.pop(field, None)
                res_id = vals.pop('id')
                if vals:
                    data.setdefault(res_id, {'old': {}, 'new': {}})[age] = vals
        for res_id in list(data.keys()):
            all_fields = set(data[res_id]['old'].keys()) | \
                set(data[res_id]['new'].keys())
            for field in all_fields:
                if data[res_id]['old'].get(field) == \
                        data[res_id]['new'].get(field):
                    del data[res_id]['old'][field]
                    del data[res_id]['new'][field]
            if data[res_id]['old'] == data[res_id]['new']:
                del data[res_id]
        return data

    def log(self, method, old_values=None, new_values=None):
        self.ensure_one()
        if old_values or new_values:
            data = self._format_data_to_log(old_values, new_values)
            AuditLog = self.env['audit.log'].sudo()
            for res_id in data:
                AuditLog.create({
                    'user_id': self._uid,
                    'model_id': self.sudo().model_id.id,
                    'res_id': res_id,
                    'method': method,
                    'data': repr(data[res_id]),
                })
        return True
