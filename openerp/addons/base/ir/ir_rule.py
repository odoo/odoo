# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time
from collections import defaultdict

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval as eval


class IrRule(models.Model):
    _name = 'ir.rule'
    _order = 'model_id DESC'
    _MODES = ['read', 'write', 'create', 'unlink']

    name = fields.Char(index=True)
    active = fields.Boolean(default=True, help="If you uncheck the active field, it will disable the record rule without deleting it (if you delete a native record rule, it may be re-created when you reload the module).")
    model_id = fields.Many2one('ir.model', string='Object', index=True, required=True, ondelete="cascade")
    groups = fields.Many2many('res.groups', 'rule_group_rel', 'rule_group_id', 'group_id')
    domain_force = fields.Text(string='Domain')
    domain = fields.Binary(compute='_force_domain', string='Domain')
    perm_read = fields.Boolean(string='Apply for Read', default=True)
    perm_write = fields.Boolean(string='Apply for Write', default=True)
    perm_create = fields.Boolean(string='Apply for Create', default=True)
    perm_unlink = fields.Boolean(string='Apply for Delete', default=True)

    _sql_constraints = [
        ('no_access_rights',
         'CHECK (perm_read!=False or perm_write!=False or perm_create!=False or perm_unlink!=False)',
         'Rule must have at least one checked access right !'),
    ]

    def _eval_context_for_combinations(self):
        """Returns a dictionary to use as evaluation context for
           ir.rule domains, when the goal is to obtain python lists
           that are easier to parse and combine, but not to
           actually execute them."""
        return {'user': tools.unquote('user'),
                'time': tools.unquote('time')}

    @api.model
    def _eval_context(self):
        """Returns a dictionary to use as evaluation context for
           ir.rule domains."""
        return {'user': self.env.user, 'time': time}

    @api.depends('domain_force')
    def _force_domain(self):
        eval_context = self._eval_context()
        for rule in self:
            if rule.domain_force:
                rule.domain = expression.normalize_domain(eval(rule.domain_force, eval_context))
            else:
                rule.domain = []

    @api.depends('groups')
    def _compute_global(self):
        for rule in self:
            rule['global'] = not rule.groups

    @api.constrains('model_id')
    def _check_model_transience(self):
        if any(self.env[rule.model_id.model].is_transient() for rule in self):
            raise ValidationError(_('Rules can not be applied on Transient models.'))

    @api.constrains('model_id')
    def _check_model_name(self):
        # Don't allow rules on rules records (this model).
        if any(rule.model_id.model == self._name for rule in self):
            raise ValidationError(_('Rules can not be applied on the Record Rules model.'))

    @api.model
    @tools.ormcache('self._uid', 'model_name', 'mode')
    def _compute_domain(self, model_name, mode="read"):
        if mode not in self._MODES:
            raise ValueError('Invalid mode: %r' % (mode,))

        if self._uid == SUPERUSER_ID:
            return None

        query = """ SELECT r.id FROM ir_rule r JOIN ir_model m ON (r.model_id=m.id)
                    WHERE m.model=%s AND r.active AND r.perm_{mode}
                    AND (r.id IN (SELECT rule_group_id FROM rule_group_rel rg
                                  JOIN res_groups_users_rel gu ON (rg.group_id=gu.gid)
                                  WHERE gu.uid=%s)
                         OR r.global)
                """.format(mode=mode)
        self._cr.execute(query, (model_name, self._uid))
        rule_ids = [row[0] for row in self._cr.fetchall()]
        if not rule_ids:
            return []

        # read 'domain' as self._uid to have the correct eval context for the rules.
        rules = self.browse(rule_ids)
        rule_domain = {vals['id']: vals['domain'] for vals in rules.read(['domain'])}

        # browse user and rules as SUPERUSER_ID to avoid access errors!
        user = self.env.user
        global_domains = []                     # list of domains
        group_domains = defaultdict(list)       # {group: list of domains}
        for rule in rules.sudo():
            dom = expression.normalize_domain(rule_domain[rule.id])
            if rule.groups & user.groups_id:
                group_domains[rule.groups[0]].append(dom)
            if not rule.groups:
                global_domains.append(dom)

        # combine global domains and group domains
        if group_domains:
            group_domain = expression.OR(map(expression.OR, group_domains.values()))
        else:
            group_domain = []
        domain = expression.AND(global_domains + [group_domain])
        return domain

    @api.model
    def clear_cache(self):
        """ Deprecated, use `clear_caches` instead. """
        self.clear_caches()

    @api.model
    def domain_get(self, model_name, mode='read'):
        dom = self._compute_domain(model_name, mode)
        if dom:
            # _where_calc is called as superuser. This means that rules can
            # involve objects on which the real uid has no acces rights.
            # This means also there is no implicit restriction (e.g. an object
            # references another object the user can't see).
            query = self.env[model_name].sudo()._where_calc(dom, active_test=False)
            return query.where_clause, query.where_clause_params, query.tables
        return [], [], ['"%s"' % self.env[model_name]._table]

    @api.multi
    def unlink(self):
        res = super(IrRule, self).unlink()
        self.clear_caches()
        return res

    @api.model
    def create(self, vals):
        res = super(IrRule, self).create(vals)
        self.clear_caches()
        return res

    @api.multi
    def write(self, vals):
        res = super(IrRule, self).write(vals)
        self.clear_caches()
        return res

#
# Hack for field 'global': this field cannot be defined like others, because
# 'global' is a Python keyword. Therefore, we add it to the class by assignment.
# Note that the attribute '_module' is normally added by the class' metaclass.
#
setattr(IrRule, 'global',
        fields.Boolean(compute='_compute_global', store=True, _module=IrRule._module,
                       help="If no group is specified the rule is global and applied to everyone"))
