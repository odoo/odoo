# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv, expression
import time
from operator import itemgetter
from functools import partial
import tools
from tools.safe_eval import safe_eval as eval
from tools.misc import unquote as unquote

SUPERUSER_UID = 1

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
        return {'user': self.pool.get('res.users').browse(cr, 1, uid),
                'time':time}

    def _domain_force_get(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        eval_context = self._eval_context(cr, uid)
        for rule in self.browse(cr, uid, ids, context):
            if rule.domain_force:
                res[rule.id] = expression.normalize(eval(rule.domain_force, eval_context))
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
        return not any(isinstance(self.pool.get(rule.model_id.model), osv.osv_memory) for rule in self.browse(cr, uid, ids, context))

    _columns = {
        'name': fields.char('Name', size=128, select=1),
        'model_id': fields.many2one('ir.model', 'Object',select=1, required=True),
        'global': fields.function(_get_value, method=True, string='Global', type='boolean', store=True, help="If no group is specified the rule is global and applied to everyone"),
        'groups': fields.many2many('res.groups', 'rule_group_rel', 'rule_group_id', 'group_id', 'Groups'),
        'domain_force': fields.text('Domain'),
        'domain': fields.function(_domain_force_get, method=True, string='Domain', type='text'),
        'perm_read': fields.boolean('Apply For Read'),
        'perm_write': fields.boolean('Apply For Write'),
        'perm_create': fields.boolean('Apply For Create'),
        'perm_unlink': fields.boolean('Apply For Delete')
    }

    _order = 'model_id DESC'

    _defaults = {
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
        (_check_model_obj, 'Rules are not supported for osv_memory objects !', ['model_id'])
    ]

    @tools.ormcache()
    def _compute_domain(self, cr, uid, model_name, mode="read"):
        if mode not in self._MODES:
            raise ValueError('Invalid mode: %r' % (mode,))

        if uid == SUPERUSER_UID:
            return None
        cr.execute("""SELECT r.id
                FROM ir_rule r
                JOIN ir_model m ON (r.model_id = m.id)
                WHERE m.model = %s
                AND r.perm_""" + mode + """
                AND (r.id IN (SELECT rule_group_id FROM rule_group_rel g_rel
                            JOIN res_groups_users_rel u_rel ON (g_rel.group_id = u_rel.gid)
                            WHERE u_rel.uid = %s) OR r.global)""", (model_name, uid))
        rule_ids = [x[0] for x in cr.fetchall()]
        if rule_ids:
            # browse user as super-admin root to avoid access errors!
            user = self.pool.get('res.users').browse(cr, SUPERUSER_UID, uid)
            global_domains = []                 # list of domains
            group_domains = {}                  # map: group -> list of domains
            for rule in self.browse(cr, SUPERUSER_UID, rule_ids):
                # read 'domain' as UID to have the correct eval context for the rule.
                rule_domain = self.read(cr, uid, rule.id, ['domain'])['domain']
                dom = expression.normalize(rule_domain)
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

    def domain_get(self, cr, uid, model_name, mode='read', context=None):
        dom = self._compute_domain(cr, uid, model_name, mode)
        if dom:
            # _where_calc is called as superuser. This means that rules can
            # involve objects on which the real uid has no acces rights.
            # This means also there is no implicit restriction (e.g. an object
            # references another object the user can't see).
            query = self.pool.get(model_name)._where_calc(cr, 1, dom, active_test=False)
            return query.where_clause, query.where_clause_params, query.tables
        return [], [], ['"'+self.pool.get(model_name)._table+'"']

    def unlink(self, cr, uid, ids, context=None):
        res = super(ir_rule, self).unlink(cr, uid, ids, context=context)
        self._compute_domain.clear_cache(self)
        return res

    def create(self, cr, uid, vals, context=None):
        res = super(ir_rule, self).create(cr, uid, vals, context=context)
        self._compute_domain.clear_cache(self)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        res = super(ir_rule, self).write(cr, uid, ids, vals, context=context)
        self._compute_domain.clear_cache(self)
        return res

ir_rule()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

