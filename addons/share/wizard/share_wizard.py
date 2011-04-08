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

import tools
from osv import osv, fields
from osv.expression import expression
from tools.translate import _
from tools.safe_eval import safe_eval

FULL_ACCESS = ('perm_read', 'perm_write', 'perm_create', 'perm_unlink')
READ_WRITE_ACCESS = ('perm_read', 'perm_write')
READ_ONLY_ACCESS = ('perm_read',)
UID_ROOT = 1


RANDOM_PASS_CHARACTERS = [chr(x) for x in range(48, 58) + range(97, 123) + range(65, 91)]
RANDOM_PASS_CHARACTERS.remove('l') #lowercase l, easily mistaken as one or capital i
RANDOM_PASS_CHARACTERS.remove('I') #uppercase i, easily mistaken as one or lowercase L
RANDOM_PASS_CHARACTERS.remove('O') #uppercase o, mistaken with zero
RANDOM_PASS_CHARACTERS.remove('o') #lowercase o, mistaken with zero
RANDOM_PASS_CHARACTERS.remove('0') #zero, mistaken with o-letter
RANDOM_PASS_CHARACTERS.remove('1') #one, mistaken with lowercase-L or capital i
def generate_random_pass():
    pass_chars = RANDOM_PASS_CHARACTERS[:]
    random.shuffle(pass_chars)
    return ''.join(pass_chars[0:10])


class share_create(osv.osv_memory):
    __logger = logging.getLogger('share.wizard')
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

    def has_extended_share(self, cr, uid, context=None):
        return self.has_group(cr, uid, module='share', group_xml_id='group_share_user_extended', context=context)

    def _has_email(self, cr, uid, ids, name, arg, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        has_email = bool(user.user_email)
        return dict([(id,has_email) for id in ids])

    def _user_type_selection(self, cr, uid, context=None):
        result = [('new','New users (emails required)'),
                   ('existing','Existing external users')]
        if self.has_extended_share(cr, uid, context=context):
            result.append(('groups','Existing groups of users'))
        return result

    _columns = {
        'action_id': fields.many2one('ir.actions.act_window', 'Action to share', required=True,
                help="The action that opens the screen containing the data you wish to share."),
        'domain': fields.char('Domain', size=256, help="Optional domain for further data filtering"),
        'user_type': fields.selection(_user_type_selection,'Users to share with',
                     help="Select the type of user(s) you would like to share data with."),
        'user_ids': fields.many2many('res.users', 'share_wizard_res_user_rel', 'share_id', 'user_id', 'Existing users', domain=[('share', '=', True)]),
        'group_ids': fields.many2many('res.groups', 'share_wizard_res_group_rel', 'share_id', 'group_id', 'Existing groups', domain=[('share', '=', False)]),
        'new_users': fields.text("New users"),
        'access_mode': fields.selection([('readwrite','Read & Write'),('readonly','Read-only')],'Access Mode'),
        'result_line_ids': fields.one2many('share.wizard.result.line', 'share_wizard_id', 'Summary', readonly=True),
        'share_root_url': fields.char('Generic Share Access URL', size=512, readonly=True, tooltip='Main access page for users that are granted shared access'),

        # used to display a warning message at first step
        'has_user_email': fields.function(_has_email, string='Has email', method=True, type="boolean"),
    }
    _defaults = {
        'user_type' : lambda self, cr, uid, *a: 'existing' if self.pool.get('res.users').search(cr, uid, [('share', '=', True)]) else 'new',
        'domain': lambda self, cr, uid, context, *a: context.get('domain', '[]'),
        'share_root_url': lambda self, cr, uid, context, *a: context.get('share_root_url') or _('Please specify "share_root_url" in context'),
        'action_id': lambda self, cr, uid, context, *a: context.get('action_id'),
        'access_mode': 'readonly',
    }

    def go_step_1(self, cr, uid, ids, context=None):
        dummy, step1_form_view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'share', 'share_step1_form')
        return {
            'name': _('Configure shared access'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'share.wizard',
            'view_id': False,
            'res_id': ids[0],
            'views': [(step1_form_view_id, 'form'), (False, 'tree'), (False, 'calendar'), (False, 'graph')],
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _create_share_group(self, cr, uid, wizard_data, context=None):
        group_obj = self.pool.get('res.groups')
        share_group_name = '%s: %s (%d-%s)' %('Sharing', wizard_data.action_id.res_model, uid, time.time())
        # create share group without putting admin in it
        return group_obj.create(cr, UID_ROOT, {'name': share_group_name, 'share': True}, {'noadmin': True})

    def _create_new_share_users(self, cr, uid, wizard_data, group_id, context=None):
        user_obj = self.pool.get('res.users')
        current_user = user_obj.browse(cr, uid, uid, context=context)
        user_ids = []
        if wizard_data.user_type == 'new':
            for new_user in wizard_data.new_users.split('\n'):
                # attempt to show more user-friendly msg than default constraint error
                existing = user_obj.search(cr, UID_ROOT, [('login', '=', new_user)])
                self._assert(not existing,
                             _('This username (%s) already exists, perhaps data has already been shared with this person.\nYou may want to try selecting existing shared users instead.') % new_user,
                             context=context)
                user_id = user_obj.create(cr, UID_ROOT, {
                        'login': new_user,
                        'password': generate_random_pass(),
                        'name': new_user,
                        'user_email': new_user,
                        'groups_id': [(6,0,[group_id])],
                        'share': True,
                        'company_id': current_user.company_id and current_user.company_id.id
                })
                user_ids.append(user_id)
        return user_ids

    def _create_shortcut(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        new_context = context.copy()
        for key in context:
            if key.startswith('default_'):
                del new_context[key]

        dataobj = self.pool.get('ir.model.data')
        menu_id = dataobj._get_id(cr, uid, 'base', 'menu_administration_shortcut', new_context)
        shortcut_menu_id  = int(dataobj.read(cr, uid, menu_id, ['res_id'], new_context)['res_id'])
        action_id = self.pool.get('ir.actions.act_window').create(cr, UID_ROOT, values, new_context)
        menu_data = {'name': values['name'],
                     'sequence': 10,
                     'action': 'ir.actions.act_window,'+str(action_id),
                     'parent_id': shortcut_menu_id,
                     'icon': 'STOCK_JUSTIFY_FILL'}
        menu_obj = self.pool.get('ir.ui.menu')
        menu_id =  menu_obj.create(cr, UID_ROOT, menu_data)
        sc_data= {'name': values['name'], 'sequence': UID_ROOT,'res_id': menu_id }
        sc_menu_id = self.pool.get('ir.ui.view_sc').create(cr, uid, sc_data, new_context)

        # update menu cache
        user_groups = set(self.pool.get('res.users').read(cr, UID_ROOT, uid, ['groups_id'])['groups_id'])
        key = (cr.dbname, shortcut_menu_id, tuple(user_groups))
        menu_obj._cache[key] = True
        return action_id


    def _cleanup_action_context(self, context_str, user_id):
        """Returns a dict representing the context_str evaluated (literal_eval) as
           a dict where items that are not useful for shared actions
           have been removed. If the evaluation of context_str as a
           dict fails, context_str is returned unaltered.

           :param user_id: the integer uid to be passed as 'uid' in the
                           evaluation context
           """
        result = False
        if context_str:
            try:
                context = safe_eval(context_str, {'uid': user_id})
                result = dict(context)
                for key in context:
                    # Remove all context keys that seem to toggle default
                    # filters based on the current user, which make no sense
                    # for shared users
                    if key and key.startswith('search_default_') and 'user_id' in key:
                        result.pop(key)
            except (NameError, ValueError):
                self.__logger.debug("Failed to cleanup action context as it does not parse server-side", exc_info=True)
                result = context_str
        return result

    def _setup_action_and_shortcut(self, cr, uid, wizard_data, user_ids, new_users, context=None):
        """Create a shortcut to reach the shared data, as well as the corresponding action, for
           each user in ``user_ids``, and assign it as their home action."""
        user_obj = self.pool.get('res.users')
        menu_action_id = user_obj._get_menu(cr, uid, context=context)
        for user_id in user_ids:
            values = {
                'name': (_('%s (Shared)') % wizard_data.action_id.name)[:64],
                'domain': wizard_data.domain,
                'context': self._cleanup_action_context(wizard_data.action_id.context, user_id),
                'res_model': wizard_data.action_id.res_model,
                'view_mode': wizard_data.action_id.view_mode,
                'view_type': wizard_data.action_id.view_type,
                'search_view_id': wizard_data.action_id.search_view_id.id,
            }
            action_id = self._create_shortcut(cr, user_id, values)
            if new_users:
                user_obj.write(cr, UID_ROOT, [user_id], {'action_id': action_id})
            else:
                user_obj.write(cr, UID_ROOT, [user_id], {'action_id': menu_action_id})

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
        for field in model_osv._columns.values() + [x[2] for x in model_osv._inherit_fields.itervalues()]:
            if field._type in ttypes and field._obj not in models:
                relation_model_id = model_obj.search(cr, UID_ROOT, [('model','=',field._obj)])[0]
                if field._type == 'one2many':
                    relation_field = '%s.%s'%(field._fields_id, suffix) if suffix else field._fields_id
                else:
                    # TODO: add some filtering for m2m and m2o - not always possible...
                    relation_field = None
                model_browse = model_obj.browse(cr, UID_ROOT, relation_model_id, context=context)
                local_rel_fields.append((relation_field, model_browse))
                for parent in self.pool.get(model_browse.model)._inherits:
                    if parent not in models:
                        parent_model = self.pool.get(parent)
                        parent_model_browse = model_obj.browse(cr, UID_ROOT,
                                                               model_obj.search(cr, UID_ROOT, [('model','=',parent)]))[0]
                        if relation_field and (field._fields_id in parent_model._columns or \
                                               field._fields_id in parent_model_inherit_fields):
                            local_rel_fields.append((relation_field, parent_model_browse))
                        else:
                            # TODO: can we setup a proper rule to restrict inherited models
                            # in case the parent does not contain the reverse m2o?
                            local_rel_fields.append((None, parent_model_browse))
                if relation_model_id != model.id and field._type in ['one2many', 'many2many']:
                    local_rel_fields += self._get_recursive_relations(cr, uid, model_browse,
                        [field._type], relation_fields + local_rel_fields, suffix=relation_field, context=context)
        return local_rel_fields

    def _get_relationship_classes(self, cr, uid, model, context=None):
        # obj0 class and its parents
        obj0 = [(None, model)]
        model_obj = self.pool.get(model.model)
        ir_model_obj = self.pool.get('ir.model')
        for parent in model_obj._inherits:
            parent_model_browse = ir_model_obj.browse(cr, UID_ROOT,
                    ir_model_obj.search(cr, UID_ROOT, [('model','=',parent)]))[0]
            obj0 += [(None, parent_model_browse)]

        obj1 = self._get_recursive_relations(cr, uid, model, ['one2many'], context=context)
        obj2 = self._get_recursive_relations(cr, uid, model, ['one2many', 'many2many'], context=context)
        obj3 = self._get_recursive_relations(cr, uid, model, ['many2one'], context=context)
        for dummy, model in obj1:
            obj3 += self._get_recursive_relations(cr, uid, model, ['many2one'], context=context)
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
        self.__logger.debug("Current user access matrix: %r", current_user_access_map)
        self.__logger.debug("New group current access matrix: %r", group_access_map)

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
                self.__logger.debug("Creating access right for model %s with values: %r", model.model, values)

    def _link_or_copy_current_user_rules(self, cr, current_user, group_id, fields_relations, context=None):
        rule_obj = self.pool.get('ir.rule')
        completed_models = set()
        for group in current_user.groups_id:
            for dummy, model in fields_relations:
                if model.id in completed_models:
                    continue
                completed_models.add(model.id)
                for rule in group.rule_groups:
                    if rule.model_id == model.id:
                        if 'user.' in rule.domain_force:
                            # Above pattern means there is likely a condition
                            # specific to current user, so we must copy the rule using
                            # the evaluated version of the domain.
                            # And it's better to copy one time too much than too few
                            rule_obj.copy(cr, UID_ROOT, rule.id, default={
                                'name': '%s (%s)' %(rule.name, _('(Copy for sharing)')),
                                'groups': [(6,0,[group_id])],
                                'domain_force': rule.domain, # evaluated version!
                            })
                            self.__logger.debug("Copying rule %s (%s) on model %s with domain: %s", rule.name, rule.id, model.model, rule.domain_force)
                        else:
                            # otherwise we can simply link the rule to keep it dynamic
                            rule_obj.write(cr, 1, [rule.id], {
                                    'groups': [(4,group_id)]
                                })
                            self.__logger.debug("Linking rule %s (%s) on model %s with domain: %s", rule.name, rule.id, model.model, rule.domain_force)

    def _create_or_combine_sharing_rule(self, cr, current_user, wizard_data, group_id, model_id, domain, rule_name=None, context=None):
        rule_obj = self.pool.get('ir.rule')
        if rule_name is None:
            rule_name = _('Sharing filter created by user %s (%s) for group %s') % \
                            (current_user.name, current_user.login, group_id)
        # if the target group already has one or more rules for the given model,
        # we should instead add the new domain to each rule with OR operator to
        # achieve the desired effect, otherwise they would be AND'ed as happens
        # for any pair of rules on the same group for the same model.
        # Indeed, A v (B /\ C) == (A v B) /\ (A v C)
        rule_ids = rule_obj.search(cr, UID_ROOT, [('groups', 'in', group_id), ('model_id', '=', model_id)])
        if rule_ids:
            for rule in rule_obj.browse(cr, UID_ROOT, rule_ids, context=context):
                if rule.domain_force == domain:
                    # skip identical ones!
                    continue
                # sanity check: the rule we are about to modify must not be used by another group
                self._assert(len(rule.groups) == 1,
                             _('Sorry, the selected group(s) currently have security rules in conflict with '\
                               'the access point you are adding, and these rules cannot be altered because they are used '\
                               'by other groups as well. Please correct it and make sure each group does not share any '\
                               'security rule with other groups (global rules are fine).'), context=context)
                # combine both domains with 'OR'
                combined_domain = rule_obj.domain_disjunction(cr, UID_ROOT, rule.domain_force, domain)
                rule.write({'domain_force': combined_domain}, context=context)
                self.__logger.debug("Combined new sharing rule on model %s with domain: %s with existing one(s): %r", model_id, domain, combined_domain)
        else:
            rule_obj.create(cr, UID_ROOT, {
                'name': rule_name,
                'model_id': model_id,
                'domain_force': domain,
                'groups': [(4,group_id)]
                })
            self.__logger.debug("Created sharing rule on model %s with domain: %s", model_id, domain)


    def _create_indirect_sharing_rules(self, cr, current_user, wizard_data, group_id, fields_relations, context=None):
        rule_obj = self.pool.get('ir.rule')
        rule_name = _('Indirect sharing filter created by user %s (%s) for group %s') % \
                            (current_user.name, current_user.login, group_id)
        try:
            domain = safe_eval(wizard_data.domain)
            if domain:
                domain_expr = expression(domain)
                for rel_field, model in fields_relations:
                    related_domain = []
                    for element in domain:
                        if domain_expr._is_leaf(element):
                            left, operator, right = element
                            left = '%s.%s'%(rel_field, left)
                            element = left, operator, right
                        related_domain.append(element)
                    self._create_or_combine_sharing_rule(cr, current_user, wizard_data,
                         group_id, model_id=model.id, domain=str(related_domain),
                         rule_name=rule_name, context=context)
        except Exception:
            self.__logger.exception('Failed to create share access')
            raise osv.except_osv(_('Sharing access could not be created'),
                                 _('Sorry, the current screen and filter you are trying to share are not supported at the moment.\nYou may want to try a simpler filter.'))

    def _create_result_lines(self, cr, uid, wizard_data, context=None):
        user_obj = self.pool.get('res.users')
        result_obj = self.pool.get('share.wizard.result.line')
        share_root_url = wizard_data.share_root_url
        format_url = '%(login)s' in share_root_url\
                 and '%(password)s' in share_root_url\
                 and '%(dbname)s' in share_root_url
        existing_passwd_str = _('*usual password*')
        if wizard_data.user_type == 'new':
            # new users
            for email in wizard_data.new_users.split('\n'):
                user_id = user_obj.search(cr, UID_ROOT, [('login', '=', email)], context=context)
                password = user_obj.read(cr, UID_ROOT, user_id[0], ['password'])['password']
                share_url = share_root_url % \
                        {'login': email,
                         'password': password,
                         'dbname': cr.dbname} if format_url else share_root_url
                result_obj.create(cr, uid, {
                        'share_wizard_id': wizard_data.id,
                        'login': email,
                        'password': password,
                        'share_url': share_url,
                    }, context=context)
        elif wizard_data.user_type == 'existing':
            # existing users
            for user in wizard_data.user_ids:
                share_url = share_root_url % \
                        {'login': user.login,
                         'password': '',
                         'dbname': cr.dbname} if format_url else share_root_url
                result_obj.create(cr, uid, {
                        'share_wizard_id': wizard_data.id,
                        'login': user.login,
                        'password': existing_passwd_str,
                        'share_url': share_url,
                        'newly_created': False,
                    }, context=context)
        else:
            # existing groups
            for group in wizard_data.group_ids:
                for user in group.users:
                    share_url = share_root_url % \
                            {'login': user.login,
                             'password': '',
                             'dbname': cr.dbname} if format_url else share_root_url
                    result_obj.create(cr, uid, {
                            'share_wizard_id': wizard_data.id,
                            'login': user.login,
                            'password': existing_passwd_str,
                            'share_url': share_url,
                            'newly_created': False,
                        }, context=context)

    def _check_preconditions(self, cr, uid, wizard_data, context=None):
        self._assert(wizard_data.action_id and wizard_data.access_mode,
                     _('Action and Access Mode are required to create a shared access point'),
                     context=context)
        self._assert(self.has_share(cr, uid, context=context),
                     _('You must be a member of the Share/User group to use the share wizard'),
                     context=context)
        if wizard_data.user_type == 'new':
            self._assert(wizard_data.new_users,
                     _('Please indicate the emails of the persons to share with, one per line'),
                     context=context)
        elif wizard_data.user_type == 'existing':
            self._assert(wizard_data.user_ids,
                     _('Please select at least one user to share with'),
                     context=context)
        elif wizard_data.user_type == 'groups':
            self._assert(wizard_data.group_ids,
                     _('Please select at least one group to share with'),
                     context=context)

    def _create_share_users_groups(self, cr, uid, wizard_data, context=None):
        """Create the appropriate shared users and groups, and return the new group_ids)
           to which the shared access should be granted.
        """
        group_ids = []
        user_ids = []
        if wizard_data.user_type == 'groups':
            group_id = None
            group_ids.extend([g.id for g in wizard_data.group_ids])
        else:
            group_id = self._create_share_group(cr, uid, wizard_data, context=context)
            group_ids.append(group_id)
        if wizard_data.user_type == 'new':
            user_ids = self._create_new_share_users(cr, uid, wizard_data, group_id, context=context)
        elif wizard_data.user_type == 'existing':
            user_ids = [x.id for x in wizard_data.user_ids]
            # reset home action to regular menu as user needs access to multiple items
            self.pool.get('res.users').write(cr, UID_ROOT, user_ids, {
                                            'groups_id': [(4,group_id)],
                                            })
        if user_ids:
            self._setup_action_and_shortcut(cr, uid, wizard_data, user_ids,
                (wizard_data.user_type == 'new'), context=context)
        return group_ids

    def go_step_2(self, cr, uid, ids, context=None):
        wizard_data = self.browse(cr, uid, ids and ids[0], context=context)
        self._check_preconditions(cr, uid, wizard_data, context=context)

        # Create shared group and users
        group_ids = self._create_share_users_groups(cr, uid, wizard_data, context=context)

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
        obj0, obj1, obj2, obj3 = self._get_relationship_classes(cr, uid, model, context=context)
        mode = wizard_data.access_mode

        rule_obj = self.pool.get('ir.rule')
        for group_id in group_ids:
            # Add access to [obj0] and [obj1] according to chosen mode
            self._add_access_rights_for_share_group(cr, uid, group_id, mode, obj0, context=context)
            self._add_access_rights_for_share_group(cr, uid, group_id, mode, obj1, context=context)

            # Add read-only access (always) to [obj2]
            self._add_access_rights_for_share_group(cr, uid, group_id, 'readonly', obj2, context=context)

            # IR.RULES
            #   A. On [obj0]: 1 rule with domain of shared action
            #   B. For each model in [obj1]: 1 rule in the form:
            #           many2one_rel.domain_of_obj0
            #        where many2one_rel is the many2one used in the definition of the
            #        one2many, and domain_of_obj0 is the sharing domain
            #        For example if [obj0] is project.project with a domain of
            #                ['id', 'in', [1,2]]
            #        then we will have project.task in [obj1] and we need to create this
            #        ir.rule on project.task:
            #                ['project_id.id', 'in', [1,2]]
            #   C. And on [obj0], [obj1], [obj2]: add all rules from all groups of
            #     the user that is sharing
            #     (Warning: rules must be copied instead of linked if they contain a reference
            #     to uid, and it must be replaced correctly)

            # A.
            self._create_or_combine_sharing_rule(cr, current_user, wizard_data,
                         group_id, model_id=model.id, domain=wizard_data.domain,
                         context=context)
            # B.
            self._create_indirect_sharing_rules(cr, current_user, wizard_data, group_id, obj1, context=context)
            # C.
            all_relations = obj0 + obj1 + obj2
            self._link_or_copy_current_user_rules(cr, current_user, group_id, all_relations, context=context)

        # so far, so good -> populate summary results and return them
        self._create_result_lines(cr, uid, wizard_data, context=context)

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

    def send_emails(self, cr, uid, ids, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if not user.user_email:
            raise osv.except_osv(_('Email required'), _('The current user must have an email address configured in User Preferences to be able to send outgoing emails.'))
        for wizard_data in self.browse(cr, uid, ids, context=context):
            for result_line in wizard_data.result_line_ids:
                email_to = result_line.login
                subject = _('%s has shared OpenERP %s information with you') % (user.name, wizard_data.action_id.name)
                body = _("Dear,\n\n%s\n\n") % subject
                body += _("To access it, you can go to the following URL:\n    %s") % result_line.share_url
                body += "\n\n"
                if result_line.newly_created:
                    body += _("You may use the following login and password to get access to this protected area:\n")
                    body += "%s: %s" % (_("Username"), result_line.login) + "\n"
                    body += "%s: %s" % (_("Password"), result_line.password) + "\n"
                    body += "%s: %s" % (_("Database"), cr.dbname) + "\n"
                else:
                    body += _("This additional data has been automatically added to your current access.\n")
                    body += _("You may use your existing login and password to view it. As a reminder, your login is %s.\n") % result_line.login

                if not tools.email_send(
                                            user.user_email,
                                            [email_to],
                                            subject,
                                            body):
                    self.__logger.warning('Failed to send sharing email from %s to %s', user.user_email, email_to)
        return {'type': 'ir.actions.act_window_close'}
share_create()

class share_result_line(osv.osv_memory):
    _name = 'share.wizard.result.line'
    _rec_name = 'login'
    _columns = {
        'login': fields.char('Username', size=64, required=True, readonly=True),
        'password': fields.char('Password', size=64, readonly=True),
        'share_url': fields.char('Share URL', size=512, required=True),
        'share_wizard_id': fields.many2one('share.wizard', 'Share Wizard', required=True),
        'newly_created': fields.boolean('Newly created', readonly=True),
    }
    _defaults = {
        'newly_created': True,
    }
share_result_line()
