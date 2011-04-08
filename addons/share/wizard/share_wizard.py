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
READ_ONLY_ACCESS = ('perm_read',)


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

    _columns = {
        'action_id': fields.many2one('ir.actions.act_window', 'Action to share', required=True,
                help="The action that opens the screen containing the data you wish to share."),
        'domain': fields.char('Domain', size=256, help="Optional domain for further data filtering"),
        'user_type': fields.selection([('existing','Existing external users'),('new','New users (emails required)')],'Users to share with',
                help="Select the type of user(s) you would like to share data with."),
        'user_ids': fields.many2many('res.users', 'share_wizard_res_user_rel', 'share_id', 'user_id', 'Existing users', domain=[('share', '=', True)]),
        'new_users': fields.text("New users"),
        'access_mode': fields.selection([('readwrite','Read & Write'),('readonly','Read-only')],'Access Mode'),
        'result_line_ids': fields.one2many('share.wizard.result.line', 'share_wizard_id', 'Summary', readonly=True),
        'share_root_url': fields.char('Generic Share Access URL', size=512, readonly=True, tooltip='Main access page for users that are granted shared access')
    }
    _defaults = {
        'user_type' : lambda self, cr, uid, *a: 'existing' if self.pool.get('res.users').search(cr, uid, [('share', '=', True)]) else 'new',
        'domain': lambda self, cr, uid, context, *a: context.get('domain', '[]'),
        'share_root_url': lambda self, cr, uid, context, *a: context.get('share_root_url') or _('Please specify "share_root_url" in context'),
        'action_id': lambda self, cr, uid, context, *a: context.get('action_id'),
        'access_mode': 'readonly'
    }

    def go_step_1(self, cr, uid, ids, context=None):
        dummy, step1_form_view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'share', 'share_step1_form')
        return {
            'name': _('Sharing Wizard - Step 1'),
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
        return group_obj.create(cr, 1, {'name': share_group_name, 'share': True}, {'noadmin': True})

    def _create_new_share_users(self, cr, uid, wizard_data, group_id, context=None):
        user_obj = self.pool.get('res.users')
        current_user = user_obj.browse(cr, uid, uid, context=context)
        user_ids = []
        if wizard_data.user_type == 'new':
            for new_user in wizard_data.new_users.split('\n'):
                # attempt to show more user-friendly msg than default constraint error
                existing = user_obj.search(cr, 1, [('login', '=', new_user)])
                if existing:
                    raise osv.except_osv(_('User already exists'),
                                         _('This username (%s) already exists, perhaps data has already been shared with this person.\nYou may want to try selecting existing shared users instead.') % new_user)
                user_id = user_obj.create(cr, 1, {
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
        action_id = self.pool.get('ir.actions.act_window').create(cr, 1, values, new_context)
        menu_data = {'name': values['name'],
                     'sequence': 10,
                     'action': 'ir.actions.act_window,'+str(action_id),
                     'parent_id': shortcut_menu_id,
                     'icon': 'STOCK_JUSTIFY_FILL'}
        menu_obj = self.pool.get('ir.ui.menu')
        menu_id =  menu_obj.create(cr, 1, menu_data)
        sc_data= {'name': values['name'], 'sequence': 1,'res_id': menu_id }
        sc_menu_id = self.pool.get('ir.ui.view_sc').create(cr, uid, sc_data, new_context)

        # update menu cache
        user_groups = set(self.pool.get('res.users').read(cr, 1, uid, ['groups_id'])['groups_id'])
        key = (cr.dbname, shortcut_menu_id, tuple(user_groups))
        menu_obj._cache[key] = True
        return action_id


    def _setup_action_and_shortcut(self, cr, uid, wizard_data, user_ids, new_users, context=None):
        user_obj = self.pool.get('res.users')
        menu_action_id = user_obj._get_menu(cr, uid, context=context)
        values = {
            'name': (_('%s (Shared)') % wizard_data.action_id.name)[:64],
            'domain': wizard_data.domain,
            'context': wizard_data.action_id.context,
            'res_model': wizard_data.action_id.res_model,
            'view_mode': wizard_data.action_id.view_mode,
            'view_type': wizard_data.action_id.view_type,
            'search_view_id': wizard_data.action_id.search_view_id.id,
        }
        for user_id in user_ids:
            action_id = self._create_shortcut(cr, user_id, values)
            if new_users:
                user_obj.write(cr, 1, [user_id], {'action_id': action_id})
            else:
                user_obj.write(cr, 1, [user_id], {'action_id': menu_action_id})

    def _get_recursive_relations(self, cr, uid, model, ttypes, relation_fields=None, suffix=None, context=None):
        """Returns list of tuples representing recursive relationships of type ``ttypes`` starting from
           model with ID ``model_id``.

           @param model: browsable model to start loading relationships from
           @param ttypes: list of relationship types to follow (e.g: ['one2many','many2many'])
           @param relation_fields: list of previously followed relationship tuples - to avoid duplicates
                                   during recursion
           @param suffix: optional suffix to append to the field path to reach the main object
        """
        
        if relation_fields is None:
            relation_fields = []
        local_rel_fields = []
        models = [x[1].model for x in relation_fields]
        model_obj = self.pool.get('ir.model')
        model_osv = self.pool.get(model.model)
        for field in model_osv._columns.values() + [x[2] for x in model_osv._inherit_fields.itervalues()]:
            if field._type in ttypes and field._obj not in models:
                relation_model_id = model_obj.search(cr, uid, [('model','=',field._obj)])[0]
                if field._type == 'one2many':
                    relation_field = '%s.%s'%(field._fields_id, suffix) if suffix else field._fields_id
                else:
                    relation_field = None # TODO: add some filtering for m2m and m2o - not always possible...
                model_browse = model_obj.browse(cr, uid, relation_model_id, context=context)
                local_rel_fields.append((relation_field, model_browse))
                if relation_model_id != model.id and field._type in ['one2many', 'many2many']:
                    local_rel_fields += self._get_recursive_relations(cr, uid, model_browse,
                        [field._type], relation_fields + local_rel_fields, suffix=relation_field, context=context)
        return local_rel_fields

    def _get_relationship_classes(self, cr, uid, model, context=None):
        obj0 = [(None, model)]
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

    def _add_access_rights_for_share_group(self, cr, uid, group_id, mode,
        fields_relations, context=None):
        """Adds access rights to group_id on object models referenced in ``fields_relations``,
           intersecting with access rights of current user to avoid granting too much rights
        """
        model_access_obj = self.pool.get('ir.model.access')
        user_obj = self.pool.get('res.users')
        target_model_ids = [x[1].id for x in fields_relations] 
        perms_to_add = (mode == 'readonly') and READ_ONLY_ACCESS or FULL_ACCESS
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
                model_access_obj.create(cr, 1, values)
                self.__logger.debug("Creating access right for model %s with values: %r", model.model, values)

    def _link_or_copy_current_user_rules(self, cr, uid, group_id, fields_relations, context=None):
        user_obj = self.pool.get('res.users')
        rule_obj = self.pool.get('ir.rule')
        current_user = user_obj.browse(cr, uid, uid, context=context)
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
                            rule_obj.copy(cr, 1, rule.id, default={
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

    def _create_indirect_sharing_rules(self, cr, uid, wizard_data, group_id, fields_relations, context=None):
        user_obj = self.pool.get('res.users')
        current_user = user_obj.browse(cr, uid, uid, context=context)
        rule_obj = self.pool.get('ir.rule')
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
                    rule_obj.create(cr, 1, {
                        'name': _('Indirect sharing filter created by user %s (%s) for group %s') % \
                            (current_user.name, current_user.login, group_id),
                        'model_id': model.id,
                        'domain_force': str(related_domain),
                        'groups': [(4,group_id)]
                    })
                    self.__logger.debug("Created indirect rule on model %s with domain: %s", model.model, repr(related_domain))
        except Exception:
            self.__logger.exception('Failed to create share access')
            raise osv.except_osv(_('Sharing access could not be setup'),
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
            for email in wizard_data.new_users.split('\n'):
                user_id = user_obj.search(cr, 1, [('login', '=', email)], context=context)
                password = user_obj.read(cr, 1, user_id[0], ['password'])['password']
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
        else:
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

    def go_step_2(self, cr, uid, ids, context=None):
        wizard_data = self.browse(cr, uid, ids and ids[0], context=context)
        assert wizard_data.action_id and wizard_data.access_mode and \
                ((wizard_data.user_type == 'new' and wizard_data.new_users) or \
                    (wizard_data.user_type == 'existing' and wizard_data.user_ids))

        # Create shared group and users
        group_id = self._create_share_group(cr, uid, wizard_data, context=context)
        user_obj = self.pool.get('res.users')
        current_user = user_obj.browse(cr, uid, uid, context=context)
        if wizard_data.user_type == 'new':
            user_ids = self._create_new_share_users(cr, uid, wizard_data, group_id, context=context)
        else:
            user_ids = [x.id for x in wizard_data.user_ids]
            # reset home action to regular menu as user needs access to multiple items
            user_obj.write(cr, 1, user_ids, {
                                   'groups_id': [(4,group_id)],
                            })
        self._setup_action_and_shortcut(cr, uid, wizard_data, user_ids, 
            (wizard_data.user_type == 'new'), context=context)


        model_obj = self.pool.get('ir.model')
        model_id = model_obj.search(cr, uid, [('model','=', wizard_data.action_id.res_model)])[0]
        model = model_obj.browse(cr, uid, model_id, context=context)

        # ACCESS RIGHTS
        # We have several classes of objects that should receive different access rights:
        # Let:
        #   - [obj0] be the target model itself
        #   - [obj1] be the target model and all other models recursively accessible from
        #            obj0 via one2many relationships
        #   - [obj2] be the target model and all other models recursively accessible from
        #            obj0 via one2many and many2many relationships
        #   - [obj3] be all models recursively accessible from obj1 via many2one relationships
        obj0, obj1, obj2, obj3 = self._get_relationship_classes(cr, uid, model, context=context)
        mode = wizard_data.access_mode

        # Add access to [obj0] and [obj1] according to chosen mode   
        self._add_access_rights_for_share_group(cr, uid, group_id, mode, obj0, context=context)
        self._add_access_rights_for_share_group(cr, uid, group_id, mode, obj1, context=context)

        # Add read-only access (always) to [obj2] and [obj3]
        self._add_access_rights_for_share_group(cr, uid, group_id, 'readonly', obj2, context=context)
        self._add_access_rights_for_share_group(cr, uid, group_id, 'readonly', obj3, context=context)


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
        #   C. And on [obj0], [obj1], [obj2], [obj3]: add all rules from all groups of 
        #     the user that is sharing 
        #     (Warning: rules must be copied instead of linked if they contain a reference 
        #     to uid, and it must be replaced correctly)
        rule_obj = self.pool.get('ir.rule')
        # A.
        rule_obj.create(cr, 1, {
            'name': _('Sharing filter created by user %s (%s) for group %s') % \
                        (current_user.name, current_user.login, group_id),
            'model_id': model.id,
            'domain_force': wizard_data.domain,
            'groups': [(4,group_id)]
            })
        # B.
        self._create_indirect_sharing_rules(cr, uid, wizard_data, group_id, obj1, context=context)
        # C.
        all_relations = obj0 + obj1 + obj2 + obj3
        self._link_or_copy_current_user_rules(cr, uid, group_id, all_relations, context=context)
        # so far, so good -> populate summary results and return them
        self._create_result_lines(cr, uid, wizard_data, context=context)

        dummy, step2_form_view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'share', 'share_step2_form')
        return {
            'name': _('Sharing Wizard - Step 2'),
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
