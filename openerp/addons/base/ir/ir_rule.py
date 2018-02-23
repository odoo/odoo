# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from openerp import SUPERUSER_ID
from openerp import tools
from openerp.osv import fields, osv, expression
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.misc import unquote as unquote

class ir_rule(osv.osv):
    _name = 'ir.rule'
    _order = 'name'
    _MODES = ['read', 'write', 'create', 'unlink']

    def _eval_context_for_combinations(self):
        """Returns a dictionary to use as evaluation context for
           ir.rule domains, when the goal is to obtain python lists
           that are easier to parse and combine, but not to
           actually execute them."""
        return {'user': unquote('user'),
                'time': unquote('time')}

    def _eval_context(self, cr, uid):
        """Returns a dictionary to use as evaluation context for
           ir.rule domains."""
        return {'user': self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid),
                'time':time}

    def _domain_force_get(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        eval_context = self._eval_context(cr, uid)
        for rule in self.browse(cr, uid, ids, context):
            if rule.domain_force:
                res[rule.id] = expression.normalize_domain(eval(rule.domain_force, eval_context))
            else:
                res[rule.id] = []
        return res

    def _get_value(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for rule in self.browse(cr, uid, ids, context):
            if not rule.groups:
                res[rule.id] = True
            else:
                res[rule.id] = False
        return res

    def _check_model_obj(self, cr, uid, ids, context=None):
        return not any(self.pool[rule.model_id.model].is_transient() for rule in self.browse(cr, uid, ids, context))

    def _check_model_name(self, cr, uid, ids, context=None):
        # Don't allow rules on rules records (this model).
        return not any(rule.model_id.model == self._name for rule in self.browse(cr, uid, ids, context))

    _columns = {
        'name': fields.char('Name', select=1),
        'active': fields.boolean('Active', help="If you uncheck the active field, it will disable the record rule without deleting it (if you delete a native record rule, it may be re-created when you reload the module."),
        'model_id': fields.many2one('ir.model', 'Object',select=1, required=True, ondelete="cascade"),
        'global': fields.function(_get_value, string='Global', type='boolean', store=True, help="If no group is specified the rule is global and applied to everyone"),
        'groups': fields.many2many('res.groups', 'rule_group_rel', 'rule_group_id', 'group_id', 'Groups'),
        'domain_force': fields.text('Domain'),
        'domain': fields.function(_domain_force_get, string='Domain', type='binary'),
        'perm_read': fields.boolean('Apply for Read'),
        'perm_write': fields.boolean('Apply for Write'),
        'perm_create': fields.boolean('Apply for Create'),
        'perm_unlink': fields.boolean('Apply for Delete')
    }

    _order = 'model_id DESC'

    _defaults = {
        'active': True,
        'perm_read': True,
        'perm_write': True,
        'perm_create': True,
        'perm_unlink': True,
        'global': True,
    }
    _sql_constraints = [
        ('no_access_rights', 'CHECK (perm_read!=False or perm_write!=False or perm_create!=False or perm_unlink!=False)', 'Rule must have at least one checked access right !'),
    ]
    _constraints = [
        (_check_model_obj, 'Rules can not be applied on Transient models.', ['model_id']),
        (_check_model_name, 'Rules can not be applied on the Record Rules model.', ['model_id']),
    ]

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
                if rule.groups & user.groups_id:
                    group_domains.setdefault(rule.groups[0], []).append(dom)
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

    def clear_cache(self, cr, uid):
        """ Deprecated, use `clear_caches` instead. """
        self.clear_caches()

    def domain_get(self, cr, uid, model_name, mode='read', context=None):
        dom = self._compute_domain(cr, uid, model_name, mode)
        if dom:
            # _where_calc is called as superuser. This means that rules can
            # involve objects on which the real uid has no acces rights.
            # This means also there is no implicit restriction (e.g. an object
            # references another object the user can't see).
            query = self.pool[model_name]._where_calc(cr, SUPERUSER_ID, dom, active_test=False)
            return query.where_clause, query.where_clause_params, query.tables
        return [], [], ['"' + self.pool[model_name]._table + '"']

    def unlink(self, cr, uid, ids, context=None):
        res = super(ir_rule, self).unlink(cr, uid, ids, context=context)
        self.clear_caches()
        return res

    def create(self, cr, uid, vals, context=None):
        res = super(ir_rule, self).create(cr, uid, vals, context=context)
        self.clear_caches()
        return res

    def write(self, cr, uid, ids, vals, context=None):
        res = super(ir_rule, self).write(cr, uid, ids, vals, context=context)
        self.clear_caches()
        return res
