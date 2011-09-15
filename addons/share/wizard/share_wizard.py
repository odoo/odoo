# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
import logging
import random
import time
from urllib import quote_plus

import tools
from osv import osv, fields
from osv import expression
from tools.translate import _
from tools.safe_eval import safe_eval

FULL_ACCESS = ('perm_read', 'perm_write', 'perm_create', 'perm_unlink')
READ_WRITE_ACCESS = ('perm_read', 'perm_write')
READ_ONLY_ACCESS = ('perm_read',)
UID_ROOT = 1

# Pseudo-domain to represent an empty filter, constructed using
# osv.expression's DUMMY_LEAF
DOMAIN_ALL = [(1, '=', 1)]

# A good selection of easy to read password characters (e.g. no '0' vs 'O', etc.)
RANDOM_PASS_CHARACTERS = 'aaaabcdeeeefghjkmnpqrstuvwxyzAAAABCDEEEEFGHJKLMNPQRSTUVWXYZ23456789'
def generate_random_pass():
    return ''.join(random.sample(RANDOM_PASS_CHARACTERS,10))


# Utils for introspecting the ORM - could be moved to server someday
class column_info(object):
    """Struct containing details about an osv column, either one local to
       its model, or one inherited via _inherits.

       :attr name: name of the column
       :attr column: column instance, subclass of osv.fields.column
       :attr parent_model: if the column is inherited, name of the model
                           that contains it, None for local columns.
       :attr parent_column: the name of the column containing the m2o
                            relationship to the parent model that contains
                            this column, None for local columns.
    """
    def __init__(self, name, column, parent_model=None, parent_column=None):
        self.name = name
        self.column = column
        self.parent_model = parent_model
        self.parent_column = parent_column

def get_column_infos(osv_model):
    """Returns a dict mapping all fields names (direct fields and
       inherited field via _inherits) to a ``column_info`` struct
       giving detailed columns """
    result = {}
    for k, (parent,m2o,col) in osv_model._inherit_fields.iteritems():
        result[k] = column_info(k, col, parent, m2o)
    for k, v in osv_model._columns.iteritems():
        result[k] = column_info(k,v)
    return result


class share_wizard(osv.osv_memory):
    _logger = logging.getLogger('share.wizard')
    _name = 'share.wizard'
    _description = 'Share Wizard'

    def _assert(self, condition, error_message, context=None):
        """Raise a user error with the given message if condition is not met.
           The error_message should have been translated with _().
        """
        if not condition:
            raise osv.except_osv(_('Sharing access could not be created'), error_message)

    def has_group(self, cr, uid, module, group_xml_id, context=None):
        """Returns True if current user is a member of the group identified by the module, group_xml_id pair."""
        # if the group was deleted or does not exist, we say NO (better safe than sorry)
        try:
            model, group_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, module, group_xml_id)
        except ValueError:
            return False
        return group_id in self.pool.get('res.users').read(cr, uid, uid, ['groups_id'], context=context)['groups_id']

    def has_share(self, cr, uid, context=None):
        return self.has_group(cr, uid, module='share', group_xml_id='group_share_user', context=context)

    def has_email(self, cr, uid, context=None):
        return bool(self.pool.get('res.users').browse(cr, uid, uid, context=context).user_email)

    def view_init(self, cr, uid, fields_list, context=None):
        if not self.has_email(cr, uid, context=context):
            raise osv.except_osv(_('No e-mail address configured'),
                                 _('You must configure your e-mail address in the user preferences before using the Share button.'))
        return super(share_wizard, self).view_init(cr, uid, fields_list, context=context)

    def _user_type_selection(self, cr, uid, context=None):
        """Selection values may be easily overridden/extended via inheritance"""
        return [('emails','List of emails')]

    """Override of create() to auto-compute the action name"""
    def create(self, cr, uid, values, context=None):
        if 'action_id' in values and not 'name' in values:
            action = self.pool.get('ir.actions.actions').browse(cr, uid, values['action_id'], context=context)
            values['name'] = action.name
        return super(share_wizard,self).create(cr, uid, values, context=context)

    _columns = {
        'action_id': fields.many2one('ir.actions.act_window', 'Action to share', required=True,
                help="The action that opens the screen containing the data you wish to share."),
        'domain': fields.char('Domain', size=256, help="Optional domain for further data filtering"),
        'user_type': fields.selection(_user_type_selection,'Users to share with',
                     help="Select the type of user(s) you would like to share data with."),
        'new_users': fields.text("Emails"),
        'access_mode': fields.selection([('readonly','Can view'),('readwrite','Can edit')],'Access Mode', required=True,
                                        help="Access rights to be granted on the shared documents."),
        'result_line_ids': fields.one2many('share.wizard.result.line', 'share_wizard_id', 'Summary', readonly=True),
        'share_root_url': fields.char('Share Access URL', size=512, readonly=True, tooltip='Main access page for users that are granted shared access'),
        'name': fields.char('Share Title', size=64, required=True, help="Title for the share (displayed to users as menu and shortcut name)"),
        'message': fields.text("Personal Message", help="An optional personal message, to be included in the e-mail notification."),
    }
    _defaults = {
        'user_type' : 'new',
        'domain': lambda self, cr, uid, context, *a: context.get('domain', '[]'),
        'share_root_url': lambda self, cr, uid, context, *a: context.get('share_root_url') or _('Please specify "share_root_url" in context'),
        'action_id': lambda self, cr, uid, context, *a: context.get('action_id'),
        'access_mode': 'readonly',
    }

    def go_step_1(self, cr, uid, ids, context=None):
        dummy, step1_form_view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'share', 'share_step1_form')
        return {
            'name': _('Grant instant access to your documents'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'share.wizard',
            'view_id': False,
            'res_id': ids[0],
            'views': [(step1_form_view_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _create_share_group(self, cr, uid, wizard_data, context=None):
        group_obj = self.pool.get('res.groups')
        share_group_name = '%s: %s (%d-%s)' %('Shared', wizard_data.name, uid, time.time())
        # create share group without putting admin in it
        return group_obj.create(cr, UID_ROOT, {'name': share_group_name, 'share': True}, {'noadmin': True})

    def _create_new_share_users(self, cr, uid, wizard_data, group_id, context=None):
        """Create one new res.users record for each email address provided in
           wizard_data.new_users, ignoring already existing users.
           Populates wizard_data.result_line_ids with one new line for
           each user (existing or not). New users will also have a value
           for the password field, so they can receive it by email.
           Returns the ids of the created users, and the ids of the
           ignored, existing ones."""
        user_obj = self.pool.get('res.users')
        current_user = user_obj.browse(cr, UID_ROOT, uid, context=context)
        created_ids = []
        existing_ids = []
        for new_user in (wizard_data.new_users or '').split('\n'):
            # Ignore blank lines
            new_user = new_user.strip()
            if not new_user: continue
            # Ignore the user if it already exists.
            existing = user_obj.search(cr, UID_ROOT, [('login', '=', new_user)])
            existing_ids.extend(existing)
            if existing:
                new_line = { 'user_id': existing[0],
                             'newly_created': False}
                wizard_data.write({'result_line_ids': [(0,0,new_line)]})
                continue
            new_pass = generate_random_pass()
            user_id = user_obj.create(cr, UID_ROOT, {
                    'login': new_user,
                    'password': new_pass,
                    'name': new_user,
                    'user_email': new_user,
                    'groups_id': [(6,0,[group_id])],
                    'share': True,
                    'company_id': current_user.company_id.id
            })
            new_line = { 'user_id': user_id,
                         'password': new_pass,
                         'newly_created': True}
            wizard_data.write({'result_line_ids': [(0,0,new_line)]})
            created_ids.append(user_id)
        return created_ids, existing_ids

    def _create_shortcut(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        new_context = context.copy()
        for key in context:
            if key.startswith('default_'):
                del new_context[key]

        dataobj = self.pool.get('ir.model.data')
        menu_id = dataobj._get_id(cr, uid, 'base', 'menu_administration_shortcut')
        shortcut_menu_id  = int(dataobj.read(cr, uid, menu_id, ['res_id'], new_context)['res_id'])
        action_id = self.pool.get('ir.actions.act_window').create(cr, UID_ROOT, values, new_context)
        menu_data = {'name': values['name'],
                     'sequence': 10,
                     'action': 'ir.actions.act_window,'+str(action_id),
                     'parent_id': shortcut_menu_id,
                     'icon': 'STOCK_JUSTIFY_FILL'}
        menu_obj = self.pool.get('ir.ui.menu')
        menu_id =  menu_obj.create(cr, UID_ROOT, menu_data)
        sc_data = {'name': values['name'], 'sequence': UID_ROOT,'res_id': menu_id }
        self.pool.get('ir.ui.view_sc').create(cr, uid, sc_data, new_context)

        # update menu cache
        user_groups = set(self.pool.get('res.users').read(cr, UID_ROOT, uid, ['groups_id'])['groups_id'])
        key = (cr.dbname, shortcut_menu_id, tuple(user_groups))
        menu_obj._cache[key] = True
        return action_id

    def _cleanup_action_context(self, context_str, user_id):
        """Returns a dict representing the context_str evaluated (safe_eval) as
           a dict where items that are not useful for shared actions
           have been removed. If the evaluation of context_str as a
           dict fails, context_str is returned unaltered.

           :param user_id: the integer uid to be passed as 'uid' in the
                           evaluation context
           """
        result = False
        if context_str:
            try:
                context = safe_eval(context_str, tools.UnquoteEvalContext(), nocopy=True)
                result = dict(context)
                for key in context:
                    # Remove all context keys that seem to toggle default
                    # filters based on the current user, as it makes no sense
                    # for shared users, who would not see any data by default.
                    if key and key.startswith('search_default_') and 'user_id' in key:
                        result.pop(key)
            except Exception:
                # Note: must catch all exceptions, as UnquoteEvalContext may cause many
                #       different exceptions, as it shadows builtins.
                self._logger.debug("Failed to cleanup action context as it does not parse server-side", exc_info=True)
                result = context_str
        return result

    def _shared_action_def(self, cr, uid, wizard_data, context=None):
        copied_action = wizard_data.action_id
        action_def = {
            'name': wizard_data.name,
            'domain': copied_action.domain,
            'context': self._cleanup_action_context(wizard_data.action_id.context, uid),
            'res_model': copied_action.res_model,
            'view_mode': copied_action.view_mode,
            'view_type': copied_action.view_type,
            'search_view_id': copied_action.search_view_id.id,
            'view_id': copied_action.view_id.id,
        }
        if copied_action.view_ids:
            action_def['view_ids'] = [(0,0,{'sequence': x.sequence,
                                            'view_mode': x.view_mode,
                                            'view_id': x.view_id.id })
                                      for x in copied_action.view_ids]
        return action_def

    def _setup_action_and_shortcut(self, cr, uid, wizard_data, user_ids, make_home, context=None):
        """Create a shortcut to reach the shared data, as well as the corresponding action, for
           each user in ``user_ids``, and assign it as their home action if ``make_home`` is True.
           Meant to be overridden for special cases.
        """
        values = self._shared_action_def(cr, uid, wizard_data, context=None)
        user_obj = self.pool.get('res.users')
        for user_id in user_ids:
            action_id = self._create_shortcut(cr, user_id, values)
            if make_home:
                # We do this only for new share users, as existing ones already have their initial home
                # action. Resetting to the default menu does not work well as the menu is rather empty
                # and does not contain the shortcuts in most cases.
                user_obj.write(cr, UID_ROOT, [user_id], {'action_id': action_id})

    def _get_recursive_relations(self, cr, uid, model, ttypes, relation_fields=None, suffix=None, context=None):
        """Returns list of tuples representing recursive relationships of type ``ttypes`` starting from
           model with ID ``model_id``.

           :param model: browsable model to start loading relationships from
           :param ttypes: list of relationship types to follow (e.g: ['one2many','many2many'])
           :param relation_fields: list of previously followed relationship tuples - to avoid duplicates
                                   during recursion
           :param suffix: optional suffix to append to the field path to reach the main object
        """
        if relation_fields is None:
            relation_fields = []
        local_rel_fields = []
        models = [x[1].model for x in relation_fields]
        model_obj = self.pool.get('ir.model')
        model_osv = self.pool.get(model.model)
        for colinfo in get_column_infos(model_osv).itervalues():
            coldef = colinfo.column
            coltype = coldef._type
            relation_field = None
            if coltype in ttypes and colinfo.column._obj not in models:
                relation_model_id = model_obj.search(cr, UID_ROOT, [('model','=',coldef._obj)])[0]
                relation_model_browse = model_obj.browse(cr, UID_ROOT, relation_model_id, context=context)
                relation_osv = self.pool.get(coldef._obj)
                if coltype == 'one2many':
                    # don't record reverse path if it's not a real m2o (that happens, but rarely)
                    dest_model_ci = get_column_infos(relation_osv)
                    reverse_rel = coldef._fields_id
                    if reverse_rel in dest_model_ci and dest_model_ci[reverse_rel].column._type == 'many2one':
                        relation_field = ('%s.%s'%(reverse_rel, suffix)) if suffix else reverse_rel
                local_rel_fields.append((relation_field, relation_model_browse))
                for parent in relation_osv._inherits:
                    if parent not in models:
                        parent_model = self.pool.get(parent)
                        parent_colinfos = get_column_infos(parent_model)
                        parent_model_browse = model_obj.browse(cr, UID_ROOT,
                                                               model_obj.search(cr, UID_ROOT, [('model','=',parent)]))[0]
                        if relation_field and coldef._fields_id in parent_colinfos:
                            # inverse relationship is available in the parent
                            local_rel_fields.append((relation_field, parent_model_browse))
                        else:
                            # TODO: can we setup a proper rule to restrict inherited models
                            # in case the parent does not contain the reverse m2o?
                            local_rel_fields.append((None, parent_model_browse))
                if relation_model_id != model.id and coltype in ['one2many', 'many2many']:
                    local_rel_fields += self._get_recursive_relations(cr, uid, relation_model_browse,
                        [coltype], relation_fields + local_rel_fields, suffix=relation_field, context=context)
        return local_rel_fields

    def _get_relationship_classes(self, cr, uid, model, context=None):
        """Computes the *relationship classes* reachable from the given
           model. The 4 relationship classes are:
           - [obj0]: the given model itself (and its parents via _inherits, if any)
           - [obj1]: obj0 and all other models recursively accessible from
                     obj0 via one2many relationships
           - [obj2]: obj0 and all other models recursively accessible from
                     obj0 via one2many and many2many relationships
           - [obj3]: all models recursively accessible from obj1 via many2one
                     relationships

           Each class is returned as a list of pairs [(field,model_browse)], where
           ``model`` is the browse_record of a reachable ir.model, and ``field`` is
           the dot-notation reverse relationship path coming from that model to obj0,
           or None if there is no reverse path.
           
           :return: ([obj0], [obj1], [obj2], [obj3])
           """
        # obj0 class and its parents
        obj0 = [(None, model)]
        model_obj = self.pool.get(model.model)
        ir_model_obj = self.pool.get('ir.model')
        for parent in model_obj._inherits:
            parent_model_browse = ir_model_obj.browse(cr, UID_ROOT,
                    ir_model_obj.search(cr, UID_ROOT, [('model','=',parent)]))[0]
            obj0 += [(None, parent_model_browse)]

        obj1 = self._get_recursive_relations(cr, uid, model, ['one2many'], relation_fields=obj0, context=context)
        obj2 = self._get_recursive_relations(cr, uid, model, ['one2many', 'many2many'], relation_fields=obj0, context=context)
        obj3 = self._get_recursive_relations(cr, uid, model, ['many2one'], relation_fields=obj0, context=context)
        for dummy, model in obj1:
            obj3 += self._get_recursive_relations(cr, uid, model, ['many2one'], relation_fields=obj0, context=context)
        return obj0, obj1, obj2, obj3

    def _get_access_map_for_groups_and_models(self, cr, uid, group_ids, model_ids, context=None):
        model_access_obj = self.pool.get('ir.model.access')
        user_right_ids = model_access_obj.search(cr, uid,
            [('group_id', 'in', group_ids), ('model_id', 'in', model_ids)],
            context=context)
        user_access_matrix = {}
        if user_right_ids:
            for access_right in model_access_obj.browse(cr, uid, user_right_ids, context=context):
                access_line = user_access_matrix.setdefault(access_right.model_id.model, set())
                for perm in FULL_ACCESS:
                    if getattr(access_right, perm, 0):
                        access_line.add(perm)
        return user_access_matrix

    def _add_access_rights_for_share_group(self, cr, uid, group_id, mode, fields_relations, context=None):
        """Adds access rights to group_id on object models referenced in ``fields_relations``,
           intersecting with access rights of current user to avoid granting too much rights
        """
        model_access_obj = self.pool.get('ir.model.access')
        user_obj = self.pool.get('res.users')
        target_model_ids = [x[1].id for x in fields_relations]
        perms_to_add = (mode == 'readonly') and READ_ONLY_ACCESS or READ_WRITE_ACCESS
        current_user = user_obj.browse(cr, uid, uid, context=context)

        current_user_access_map = self._get_access_map_for_groups_and_models(cr, uid,
            [x.id for x in current_user.groups_id], target_model_ids, context=context)
        group_access_map = self._get_access_map_for_groups_and_models(cr, uid,
            [group_id], target_model_ids, context=context)
        self._logger.debug("Current user access matrix: %r", current_user_access_map)
        self._logger.debug("New group current access matrix: %r", group_access_map)

        # Create required rights if allowed by current user rights and not
        # already granted
        for dummy, model in fields_relations:
            values = {
                'name': _('Copied access for sharing'),
                'group_id': group_id,
                'model_id': model.id,
            }
            current_user_access_line = current_user_access_map.get(model.model,set())
            existing_group_access_line = group_access_map.get(model.model,set())
            need_creation = False
            for perm in perms_to_add:
                if perm in current_user_access_line \
                   and perm not in existing_group_access_line:
                    values.update({perm:True})
                    group_access_map.setdefault(model.model, set()).add(perm)
                    need_creation = True
            if need_creation:
                model_access_obj.create(cr, UID_ROOT, values)
                self._logger.debug("Creating access right for model %s with values: %r", model.model, values)

    def _link_or_copy_current_user_rules(self, cr, current_user, group_id, fields_relations, context=None):
        rule_obj = self.pool.get('ir.rule')
        rules_done = set()
        for group in current_user.groups_id:
            for dummy, model in fields_relations:
                for rule in group.rule_groups:
                    if rule.id in rules_done:
                        continue
                    rules_done.add(rule.id)
                    if rule.model_id.id == model.id:
                        if 'user.' in rule.domain_force:
                            # Above pattern means there is likely a condition
                            # specific to current user, so we must copy the rule using
                            # the evaluated version of the domain.
                            # And it's better to copy one time too much than too few
                            rule_obj.copy(cr, UID_ROOT, rule.id, default={
                                'name': '%s %s' %(rule.name, _('(Copy for sharing)')),
                                'groups': [(6,0,[group_id])],
                                'domain_force': rule.domain, # evaluated version!
                            })
                            self._logger.debug("Copying rule %s (%s) on model %s with domain: %s", rule.name, rule.id, model.model, rule.domain_force)
                        else:
                            # otherwise we can simply link the rule to keep it dynamic
                            rule_obj.write(cr, 1, [rule.id], {
                                    'groups': [(4,group_id)]
                                })
                            self._logger.debug("Linking rule %s (%s) on model %s with domain: %s", rule.name, rule.id, model.model, rule.domain_force)

    def _check_personal_rule_or_duplicate(self, cr, group_id, rule, context=None):
        """Verifies that the given rule only belongs to the given group_id, otherwise
           duplicate it for the current group, and unlink the previous one.
           The duplicated rule has the original domain copied verbatim, without
           any evaluation.
           Returns the final rule to use (browse_record), either the original one if it
           only belongs to this group, or the copy."""
        if len(rule.groups) == 1:
            return rule
        # duplicate it first:
        rule_obj = self.pool.get('ir.rule')
        new_id = rule_obj.copy(cr, UID_ROOT, rule.id,
                               default={
                                       'name': '%s %s' %(rule.name, _('(Duplicated for modified sharing permissions)')),
                                       'groups': [(6,0,[group_id])],
                                       'domain_force': rule.domain_force, # non evaluated!
                               })
        self._logger.debug("Duplicating rule %s (%s) (domain: %s) for modified access ", rule.name, rule.id, rule.domain_force)
        # then disconnect from group_id:
        rule.write({'groups':[(3,group_id)]}) # disconnects, does not delete!
        return rule_obj.browse(cr, UID_ROOT, new_id, context=context)

    def _create_or_combine_sharing_rule(self, cr, current_user, wizard_data, group_id, model_id, domain, restrict=False, rule_name=None, context=None):
        """Add a new ir.rule entry for model_id and domain on the target group_id.
           If ``restrict`` is True, instead of adding a rule, the domain is
           combined with AND operator with all existing rules in the group, to implement
           an additional restriction (as of 6.1, multiple rules in the same group are
           OR'ed by default, so a restriction must alter all existing rules)

           This is necessary because the personal rules of the user that is sharing
           are first copied to the new share group. Afterwards the filters used for
           sharing are applied as an additional layer of rules, which are likely to
           apply to the same model. The default rule algorithm would OR them (as of 6.1),
           which would result in a combined set of permission that could be larger
           than those of the user that is sharing! Hence we must forcefully AND the
           rules at this stage.
           One possibly undesirable effect can appear when sharing with a
           pre-existing group, in which case altering pre-existing rules would not
           be desired. This is addressed in the portal module.
           """
        if rule_name is None:
            rule_name = _('Sharing filter created by user %s (%s) for group %s') % \
                            (current_user.name, current_user.login, group_id)
        rule_obj = self.pool.get('ir.rule')
        rule_ids = rule_obj.search(cr, UID_ROOT, [('groups', 'in', group_id), ('model_id', '=', model_id)])
        if rule_ids:
            for rule in rule_obj.browse(cr, UID_ROOT, rule_ids, context=context):
                if rule.domain_force == domain:
                    # don't create it twice!
                    if restrict:
                        continue
                    else:
                        self._logger.debug("Ignoring sharing rule on model %s with domain: %s the same rule exists already", model_id, domain)
                        return
                if restrict:
                    # restricting existing rules is done by adding the clause
                    # with an AND, but we can't alter the rule if it belongs to
                    # other groups, so we duplicate if needed
                    rule = self._check_personal_rule_or_duplicate(cr, group_id, rule, context=context)
                    eval_ctx = rule_obj._eval_context_for_combinations()
                    org_domain = expression.normalize(eval(rule.domain_force, eval_ctx))
                    new_clause = expression.normalize(eval(domain, eval_ctx))
                    combined_domain = expression.AND([new_clause, org_domain])
                    rule.write({'domain_force': combined_domain, 'name': rule.name + _('(Modified)')})
                    self._logger.debug("Combining sharing rule %s on model %s with domain: %s", rule.id, model_id, domain)
        if not restrict:
            # Adding the new rule in the group is ok for normal cases, because rules
            # in the same group and for the same model will be combined with OR
            # (as of v6.1), so the desired effect is achieved.
            rule_obj.create(cr, UID_ROOT, {
                'name': rule_name,
                'model_id': model_id,
                'domain_force': domain,
                'groups': [(4,group_id)]
                })
            self._logger.debug("Created sharing rule on model %s with domain: %s", model_id, domain)

    def _create_indirect_sharing_rules(self, cr, current_user, wizard_data, group_id, fields_relations, context=None):
        rule_name = _('Indirect sharing filter created by user %s (%s) for group %s') % \
                            (current_user.name, current_user.login, group_id)
        try:
            domain = safe_eval(wizard_data.domain)
            if domain:
                domain_expr = expression.expression(domain)
                for rel_field, model in fields_relations:
                    related_domain = []
                    if not rel_field: continue
                    for element in domain:
                        if domain_expr._is_leaf(element):
                            left, operator, right = element
                            left = '%s.%s'%(rel_field, left)
                            element = left, operator, right
                        related_domain.append(element)
                    self._create_or_combine_sharing_rule(cr, current_user, wizard_data,
                         group_id, model_id=model.id, domain=str(related_domain),
                         rule_name=rule_name, restrict=True, context=context)
        except Exception:
            self._logger.exception('Failed to create share access')
            raise osv.except_osv(_('Sharing access could not be created'),
                                 _('Sorry, the current screen and filter you are trying to share are not supported at the moment.\nYou may want to try a simpler filter.'))

    def _finish_result_lines(self, cr, uid, wizard_data, share_group_id, context=None):
        """Perform finalization of the share, and populate the summary"""
        share_root_url = wizard_data.share_root_url
        format_url = '%(dbname)s' in share_root_url
        for result in wizard_data.result_line_ids:
                # share_root_url may contain placeholders for dbname, login and password
                share_url = (share_root_url % \
                                        {'login': quote_plus(result.user_id.login),
                                         'password': '', # kept empty for security reasons
                                         'dbname': quote_plus(cr.dbname)}) \
                                          if format_url else share_root_url
                result.write({'share_url': share_url}, context=context)

    def _check_preconditions(self, cr, uid, wizard_data, context=None):
        self._assert(wizard_data.action_id and wizard_data.access_mode,
                     _('Action and Access Mode are required to create a shared access'),
                     context=context)
        self._assert(self.has_share(cr, uid, context=context),
                     _('You must be a member of the Share/User group to use the share wizard'),
                     context=context)
        if wizard_data.user_type == 'emails':
            self._assert(wizard_data.new_users,
                     _('Please indicate the emails of the persons to share with, one per line'),
                     context=context)

    def _create_share_users_group(self, cr, uid, wizard_data, context=None):
        """Creates the appropriate share group and share users, and populates
           result_line_ids of wizard_data with one line for each user.

           :return: the new group id (to which the shared access should be granted)
        """
        group_id = self._create_share_group(cr, uid, wizard_data, context=context)
        # First create any missing user, based on the email addresses provided
        new_ids, existing_ids = self._create_new_share_users(cr, uid, wizard_data, group_id, context=context)
        # Finally, setup the new action and shortcut for the users.
        if existing_ids:
            # existing users still need to join the new group
            self.pool.get('res.users').write(cr, UID_ROOT, existing_ids, {
                                                'groups_id': [(4,group_id)],
                                             })
            # existing user don't need their home action replaced, only a new shortcut
            self._setup_action_and_shortcut(cr, uid, wizard_data, existing_ids, make_home=False, context=context)
        if new_ids:
            # new users need a new shortcut AND a home action
            self._setup_action_and_shortcut(cr, uid, wizard_data, new_ids, make_home=True, context=context)
        return group_id

    def go_step_2(self, cr, uid, ids, context=None):
        wizard_data = self.browse(cr, uid, ids[0], context=context)
        self._check_preconditions(cr, uid, wizard_data, context=context)

        # Create shared group and users
        group_id = self._create_share_users_group(cr, uid, wizard_data, context=context)

        current_user = self.pool.get('res.users').browse(cr, uid, uid, context=context)

        model_obj = self.pool.get('ir.model')
        model_id = model_obj.search(cr, uid, [('model','=', wizard_data.action_id.res_model)])[0]
        model = model_obj.browse(cr, uid, model_id, context=context)

        # ACCESS RIGHTS
        # We have several classes of objects that should receive different access rights:
        # Let:
        #   - [obj0] be the target model itself (and its parents via _inherits, if any)
        #   - [obj1] be the target model and all other models recursively accessible from
        #            obj0 via one2many relationships
        #   - [obj2] be the target model and all other models recursively accessible from
        #            obj0 via one2many and many2many relationships
        #   - [obj3] be all models recursively accessible from obj1 via many2one relationships
        #            (currently not used)
        obj0, obj1, obj2, obj3 = self._get_relationship_classes(cr, uid, model, context=context)
        mode = wizard_data.access_mode

        # Add access to [obj0] and [obj1] according to chosen mode
        self._add_access_rights_for_share_group(cr, uid, group_id, mode, obj0, context=context)
        self._add_access_rights_for_share_group(cr, uid, group_id, mode, obj1, context=context)

        # Add read-only access (always) to [obj2]
        self._add_access_rights_for_share_group(cr, uid, group_id, 'readonly', obj2, context=context)

        # IR.RULES
        #   A. On [obj0], [obj1], [obj2]: add all rules from all groups of
        #     the user that is sharing
        #     Warning: rules must be copied instead of linked if they contain a reference
        #     to uid or if the rule is shared with other groups (and it must be replaced correctly)
        #   B. On [obj0]: 1 rule with domain of shared action
        #   C. For each model in [obj1]: 1 rule in the form:
        #           many2one_rel.domain_of_obj0
        #        where many2one_rel is the many2one used in the definition of the
        #        one2many, and domain_of_obj0 is the sharing domain
        #        For example if [obj0] is project.project with a domain of
        #                ['id', 'in', [1,2]]
        #        then we will have project.task in [obj1] and we need to create this
        #        ir.rule on project.task:
        #                ['project_id.id', 'in', [1,2]]

        # A.
        all_relations = obj0 + obj1 + obj2
        self._link_or_copy_current_user_rules(cr, current_user, group_id, all_relations, context=context)
        # B.
        main_domain = wizard_data.domain if wizard_data.domain != '[]' else DOMAIN_ALL
        self._create_or_combine_sharing_rule(cr, current_user, wizard_data,
                     group_id, model_id=model.id, domain=main_domain,
                     restrict=True, context=context)
        # C.
        self._create_indirect_sharing_rules(cr, current_user, wizard_data, group_id, obj1, context=context)

        # so far, so good -> check summary results and return them
        self._finish_result_lines(cr, uid, wizard_data, group_id, context=context)

        # update share URL to make it generic
        generic_share_url = wizard_data.share_root_url % {'dbname': cr.dbname,
                                                          'login': '',
                                                          'password': ''}
        wizard_data.write({'share_root_url': generic_share_url}, context=context)

        # refresh wizard_data
        wizard_data = self.browse(cr, uid, ids[0], context=context)

        # send the confirmation emails:
        self.send_emails(cr, uid, wizard_data, context=context)

        dummy, step2_form_view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'share', 'share_step2_form')
        return {
            'name': _('Shared access created!'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'share.wizard',
            'view_id': False,
            'res_id': ids[0],
            'views': [(step2_form_view_id, 'form'), (False, 'tree'), (False, 'calendar'), (False, 'graph')],
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def send_emails(self, cr, uid, wizard_data, context=None):
        self._logger.info('Sending share notifications by email...')
        mail_message = self.pool.get('mail.message')
        user = self.pool.get('res.users').browse(cr, UID_ROOT, uid)
        if not user.user_email:
            raise osv.except_osv(_('Email required'), _('The current user must have an email address configured in User Preferences to be able to send outgoing emails.'))

        # TODO: also send an HTML version of this mail
        emails_sent = 0
        for result_line in wizard_data.result_line_ids:
            email_to = result_line.user_id.user_email
            subject = wizard_data.name
            body = _("Hello,")
            body += "\n\n"
            body += _("I've shared %s with you!") % wizard_data.name
            body += "\n\n"
            body += _("The documents are not attached, you can view them online directly on my OpenERP server at:")
            body += "\n    " + result_line.share_url
            body += "\n\n"
            if wizard_data.message:
                body += wizard_data.message
                body += "\n\n"
            if result_line.newly_created:
                body += _("These are your credentials to access this protected area:\n")
                body += "%s: %s" % (_("Username"), result_line.user_id.login) + "\n"
                body += "%s: %s" % (_("Password"), result_line.password) + "\n"
                body += "%s: %s" % (_("Database"), cr.dbname) + "\n"
            else:
                body += _("The documents have been automatically added to your current OpenERP documents.\n")
                body += _("You may use your current login (%s) and password to view them.\n") % result_line.user_id.login
            body += "\n\n"
            body += user.signature
            body += "\n\n"
            body += "--\n"
            body += _("OpenERP is a powerful and user-friendly suite of Business Applications (CRM, Sales, HR, etc.)\n"
                      "It is open source and can be found on http://www.openerp.com.")

            if mail_message.schedule_with_attach(cr, uid,
                                                 user.user_email,
                                                 [email_to],
                                                 subject,
                                                 body,
                                                 model='share.wizard'):
                emails_sent += 1
            else:
                self._logger.warning('Failed to send share notification from %s to %s, ignored', user.user_email, email_to)
        self._logger.info('%s share notification(s) successfully sent.', emails_sent)
share_wizard()

class share_result_line(osv.osv_memory):
    _name = 'share.wizard.result.line'
    _rec_name = 'user_id'
    _columns = {
        'user_id': fields.many2one('res.users', required=True, readonly=True),
        'login': fields.related('user_id', 'login', string='Login', type='char', size=64, required=True, readonly=True),
        'password': fields.char('Password', size=64, readonly=True),
        'share_url': fields.char('Share URL', size=512, required=True),
        'share_wizard_id': fields.many2one('share.wizard', 'Share Wizard', required=True),
        'newly_created': fields.boolean('Newly created', readonly=True),
    }
    _defaults = {
        'newly_created': True,
    }
share_result_line()
