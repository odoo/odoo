# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

import odoo
from odoo import api, fields, models, _
from odoo import SUPERUSER_ID
from odoo import tools
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval as eval
from odoo.tools.misc import unquote as unquote


class IrRule(models.Model):
    _name = 'ir.rule'
    _order = 'name, model_id DESC'
    _MODES = ['read', 'write', 'create', 'unlink']

    def _get_value(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for rule in self.browse(cr, uid, ids, context):
            if not rule.groups:
                res[rule.id] = True
            else:
                res[rule.id] = False
        return res

    _columns = {'global': odoo.osv.fields.function(_get_value, string='Global', type='boolean', store=True, help="If no group is specified the rule is global and applied to everyone")}

    name = fields.Char(index=True)
    active = fields.Boolean(default=True, help="If you uncheck the active field, it will disable the record rule without deleting it (if you delete a native record rule, it may be re-created when you reload the module).")
    model_id = fields.Many2one('ir.model', string='Object', index=True, required=True, ondelete="cascade")
    groups = fields.Many2many('res.groups', 'rule_group_rel', 'rule_group_id', 'group_id')
    domain_force = fields.Text(string='Domain')
    domain = fields.Binary(compute='_domain_force_get', string='Domain')
    perm_read = fields.Boolean(string='Apply for Read', default=True)
    perm_write = fields.Boolean(string='Apply for Write', default=True)
    perm_create = fields.Boolean(string='Apply for Create', default=True)
    perm_unlink = fields.Boolean(string='Apply for Delete', default=True)

    _sql_constraints = [
        ('no_access_rights', 'CHECK (perm_read!=False or perm_write!=False or perm_create!=False or perm_unlink!=False)', 'Rule must have at least one checked access right !'),
    ]

    def _eval_context_for_combinations(self):
        """Returns a dictionary to use as evaluation context for
           ir.rule domains, when the goal is to obtain python lists
           that are easier to parse and combine, but not to
           actually execute them."""
        return {'user': unquote('user'),
                'time': unquote('time')}

    @api.model
    def _eval_context(self):
        """Returns a dictionary to use as evaluation context for
           ir.rule domains."""
        return {'user': self.env.user, 'time': time}

    @api.depends('domain')
    def _domain_force_get(self):
        eval_context = self._eval_context()
        for rule in self:
            if rule.domain_force:
                rule.domain = expression.normalize_domain(eval(rule.domain_force, eval_context))
            else:
                rule.domain = []

    @api.constrains('model_id')
    def _check_model_obj(self):
        if any(self.pool[rule.model_id.model].is_transient() for rule in self):
            raise UserWarning(_('Rules can not be applied on Transient models.'))

    @api.constrains('model_id')
    def _check_model_name(self):
        # Don't allow rules on rules records (this model).
        if any(rule.model_id.model == self._name for rule in self):
            raise UserWarning(_('Rules can not be applied on the Record Rules model.'))

    @tools.ormcache('uid', 'model_name', 'mode')
    def _compute_domain(self, cr, uid, model_name, mode="read"):
        if mode not in self._MODES:
            raise ValueError('Invalid mode: %r' % (mode,))

        if uid == SUPERUSER_ID:
            return None
        cr.execute("""SELECT r.id
                FROM ir_rule r
                JOIN ir_model m ON (r.model_id = m.id)
                WHERE m.model = %s
                AND r.active is True
                AND r.perm_""" + mode + """
                AND (r.id IN (SELECT rule_group_id FROM rule_group_rel g_rel
                            JOIN res_groups_users_rel u_rel ON (g_rel.group_id = u_rel.gid)
                            WHERE u_rel.uid = %s) OR r.global)""", (model_name, uid))
        rule_ids = [x[0] for x in cr.fetchall()]
        if rule_ids:
            # browse user as super-admin root to avoid access errors!
            user = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid)
            global_domains = []                 # list of domains
            group_domains = {}                  # map: group -> list of domains
            for rule in self.browse(cr, SUPERUSER_ID, rule_ids):
                # read 'domain' as UID to have the correct eval context for the rule.
                rule_domain = self.read(cr, uid, [rule.id], ['domain'])[0]['domain']
                dom = expression.normalize_domain(rule_domain)
                for group in rule.groups:
                    if group in user.groups_id:
                        group_domains.setdefault(group, []).append(dom)
                if not rule.groups:
                    global_domains.append(dom)
            # combine global domains and group domains
            if group_domains:
                group_domain = expression.OR(map(expression.OR, group_domains.values()))
            else:
                group_domain = []
            domain = expression.AND(global_domains + [group_domain])
            return domain
        return []

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
        return [], [], ['"' + self.env[model_name]._table + '"']

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
