# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, http, SUPERUSER_ID, _
from odoo.addons.web.controllers.main import clean_action, DataSet
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import consteq


class PublicProject(http.Controller):

    @http.route('/embed/project/security/check_access', type='json', auth="public")
    def check_access(self, access_token, project_id=None, task_id=None, action=None):
        """Public route to check the user's access token and access rights. Whichever is
        the highest of the two will take precedence.

        :param access_token: (str) The access token passed in the URL
        :param project_id: (int) The ID of the project (or task's project) to access
        :param task_id: (int) The ID of the task to access
        :param action: (str) (optional) The action for which to check the rights ('read' or 'edit')
        :return: if action : (bool) True if the action is permitted
                 else: (str) 'invalid' if no access granted
                             'edit' if edit access granted
                             'readonly' if readonly access granted
        """
        levels = ['invalid', 'readonly', 'edit']
        user_rights = 0
        if self._is_logged_in():
            project = request.env['project.project'].browse(project_id)
            if project.check_access_rights('write'):
                user_rights = 2  # edit rights
            elif project.check_access_rights('read'):
                user_rights = 1  # readonly rights
        if self._public_project_check_token(access_token, project_id=project_id, task_id=task_id, action='edit'):
            user_rights = 2  # edit rights
        elif self._public_project_check_token(access_token, project_id=project_id, task_id=task_id, action='read'):
            user_rights = max(1, user_rights)  # readonly rights, unless the logged user has higher rights
        if action == 'read':
            return user_rights >= 1
        if action == 'edit':
            return user_rights == 2
        return levels[user_rights]

    def _chatter_get_track_args(self, task_id, fields_to_track):
        """Get the values required by task.message_track, as well as the task itself.

        Note: Must be called before the write operation in order to get initial values.

        :param task_id: (int) The ID of the task to track
        :param fields_to_track: ([str]) The list of fields to track on the task
        :return: (Object, dict, dict) The task object, tracked fields and their initial values
        """
        task = request.env['project.task']
        task = task.sudo() if not self._is_logged_in() else task
        task = task.browse(task_id) if task_id else task
        tracked_fields = task.fields_get(fields_to_track) if task else None
        initial_values = dict([(task.id, {field: task[field] for field in fields_to_track})])
        return task, tracked_fields, initial_values

    def _chatter_track(self, task, tracked_fields, initial_values):
        """Track fields of a task for the chatter, as Public User if user is not logged in.

        :param task: (Object) The task object
        :param tracked_fields: (dict) The tracked fields
        :param initial_values: (dict) The tracked fields' initial values
        :return: True
        """
        kwargs = {'author_id': request.env.uid} if not self._is_logged_in() else {}
        task.message_track(tracked_fields, initial_values, **kwargs)
        return True

    def _check_and_perform(self, method_to_call, submethod=None, access_info=None, **kw):
        """Check permissions before calling a given method.

        :param method_to_call: (str) The name of the method to call if access is granted.
        :param submethod: (str) The name of the method that the method to call will call
                                if access is granted (if method_to_call == call or call_kw).
                                Defaults to None.
        :param kw: (dict) All args and kwargs passed to the method to call.
        :return: (any) The result of the method to call or None if no access was granted.
        """
        read_words = ['read', 'load', 'default', 'get', 'search',
                     'message', 'mail',  # we want to allow readonly users to use the chatter
                     'onchange', 'export_data']
        edit_words = ['write', 'resequence', 'set']

        if any(word in (submethod or method_to_call) for word in read_words):
            return self._check_and_perform_read(method_to_call,
                                                submethod=submethod,
                                                access_info=access_info,
                                                **kw)
        if any(word in (submethod or method_to_call) for word in edit_words):
            return self._check_and_perform_write(method_to_call,
                                                 submethod=submethod,
                                                 access_info=access_info,
                                                 **kw)
        if 'create' in (submethod or method_to_call):
            return self._check_and_perform_create(method_to_call,
                                                  submethod=submethod,
                                                  access_info=access_info,
                                                  **kw)
        return
    
    def _check_and_perform_create(self, method_to_call, submethod=None, access_info={}, **kw):
        """Check the user's create permissions. If access is granted, redirect
        to all create read methods called by project's kanban and form views,
        as sudo.

        :param method_to_call: (str) The name of the method to call if access is granted.
        :param submethod: (str) The name of the method that the method to call will call
                                if access is granted (if method_to_call == call or call_kw).
                                Defaults to None.
        :param kw: (dict) All args and kwargs passed to the method to call.
        :return: (any) The result of the method to call or None if no access was granted.
        """
        access_token = access_info.get('access_token', None)
        project_id = access_info.get('project_id')
        task_id = access_info.get('task_id')

        # If there is a valid token, perform the operation as sudo
        if access_token and self.check_access(access_token,
                                              project_id=project_id,
                                              task_id=None,
                                              action='edit'):
            model_name = kw.pop('model', None)
            model = request.env[model_name] if model_name else None
            if method_to_call == 'call':
                return self._sudo_call_kw(model, submethod, *kw.get('args', None), {})
            elif method_to_call == 'call_kw':
                return self._sudo_call_kw(model, submethod, kw.get('args', None), kw.get('kwargs', {}))
        # Otherwise if the user is logged in, perform the operation as that user
        elif self._is_logged_in():
            return getattr(self, method_to_call)(**kw)
        # If there is no valid token and the user is not logged in, raise an AccessError
        else:
            raise AccessError(_("Create rights denied."))

    def _check_and_perform_read(self, method_to_call, submethod=None, access_info={}, **kw):
        """Check the user's read permissions. If access is granted, redirect
        to all various read methods called by project's kanban and form views,
        as sudo.

        :param method_to_call: (str) The name of the method to call if access is granted.
        :param submethod: (str) The name of the method that the method to call will call
                                if access is granted (if method_to_call == call or call_kw).
                                Defaults to None.
        :param kw: (dict) All args and kwargs passed to the method to call.
        :return: (any) The result of the method to call or None if no access was granted.
        """
        access_token = access_info.get('access_token', None)
        project_id = access_info.get('project_id')
        task_id = access_info.get('task_id', None)

        # If there is a valid token, perform the operation as sudo
        if access_token and self.check_access(access_token,
                                              project_id=project_id,
                                              task_id=task_id,
                                              action='read'):
            model_name = kw.pop('model', None)
            model = request.env[model_name] if model_name else None
            if method_to_call == 'call':
                return self._sudo_call_kw(model, submethod, *kw.get('args', None), {})
            elif method_to_call == 'call_kw':
                return self._sudo_call_kw(model, submethod, kw.get('args', None), kw.get('kwargs', {}))
            elif method_to_call == 'load_action':
                return self._sudo_load_action(**kw)
            elif method_to_call == 'mail_init_messaging':
                return self._sudo_mail_init_messaging()
            elif method_to_call == 'read':
                return self._sudo_read(model, **kw.get('kwargs', {}))
            elif method_to_call == 'read_group':
                return self._sudo_read_group(model, **kw.get('kwargs', {}))
            elif method_to_call == 'read_progress_bar':
                return self._sudo_read_progress_bar(model, **kw.get('kwargs', {}))
            elif method_to_call == 'search_read':
                return self._sudo_search_read(model, **kw)
        # Otherwise if the user is logged in, perform the operation as that user
        elif self._is_logged_in():
            method_to_call = 'load' if method_to_call == 'load_action' else method_to_call
            return getattr(self, method_to_call)(**kw)
        # If there is no valid token and the user is not logged in, raise an AccessError
        else:
            raise AccessError(_("Read rights denied."))

    def _check_and_perform_write(self, method_to_call, submethod=None, access_info={}, **kw):
        """Check the user's write permissions. If access is granted, redirect
        to all various write methods called by project's kanban and form views,
        as sudo.

        :param method_to_call: (str) The name of the method to call if access is granted.
        :param submethod: (str) The name of the method that the method to call will call
                                if access is granted (if method_to_call == call or call_kw).
                                Defaults to None.
        :param kw: (dict) All args and kwargs passed to the method to call.
        :return: (any) The result of the method to call or None if no access was granted.
        """
        res = None
        access_token = access_info.get('access_token')
        project_id = access_info.get('project_id')
        task_id = access_info.get('task_id')
        fields_to_track = ['kanban_state_label', 'stage_id', 'priority']
        task, tracked_fields, initial_values = self._chatter_get_track_args(task_id, fields_to_track)

        # If there is a valid token, perform the operation as sudo
        if access_token and self.check_access(access_token,
                                              project_id=project_id,
                                              task_id=task_id,
                                              action='edit'):
            model = request.env[kw.pop('model', '')]
            if method_to_call == 'call':
                res = self._sudo_call_kw(model, submethod, *kw.get('args', None), {})
            elif method_to_call == 'call_kw':
                res = self._sudo_call_kw(model, submethod, kw.get('args', None), kw.get('kwargs', {}))
            elif method_to_call == 'resequence':
                res = self._sudo_resequence(model, **kw)
        # Otherwise if the user is logged in, perform the operation as that user
        elif self._is_logged_in():
            res = getattr(self, method_to_call)(**kw)
        # If there is no valid token and the user is not logged in, raise an AccessError
        else:
            raise AccessError(_("Edit rights denied."))
        # This has to happen after the operation was performed
        self._chatter_track(task=task, tracked_fields=tracked_fields, initial_values=initial_values)
        return res

    def _public_project_check_token(self, access_token, project_id=None, task_id=None, action='read'):
        """Check the token for a project or task, for a given action.

        Note: Access to a project implies access to its tasks but the inverse is not true. If we're trying to access
              a task, after unsuccessfully checking the task token we check the task token.

        :param access_token: (str) The access token to check
        :param project_id: (int) The ID of the project for which access is being requested
        :param task_id: (int) Optional: The ID of the task for which access is being requested
        :param action: (str) The action to perform on the project or task: 'read' or 'edit'
        :return: (bool) True if requested access is granted
        """
        res = self.__check_token_helper(access_token, 'project.task', task_id, action) if task_id else None
        return res or self.__check_token_helper(access_token, 'project.project', project_id, action)

    def __check_token_helper(self, access_token, model, document_id, action):
        """Helper function to _public_project_check_token.

        :param access_token: (str) The access token to check
        :param model: (str) The name of the model to which the requested document belongs
        :param document_id: (str) The requested document's ID
        :param action: (str) The action to perform on the project or task: 'read' or 'edit'
        :return: (bool) True if requested access is granted
        """
        if not access_token:
            return False
        rec_sudo = request.env[model].sudo().browse(document_id)
        if action == 'read':
            rec_token = rec_sudo.access_token or rec_sudo.edit_token or None
            return (rec_token and consteq(access_token, rec_token))
        if action == 'edit':
            rec_token = rec_sudo.edit_token or None
            return (rec_token and consteq(access_token, rec_token) and rec_sudo.privacy_visibility == 'portaledit')
        return False

    def _is_logged_in(self):
        """Checks if the user is logged in.

        :return: (bool) True if the user is logged in
        """
        return request.session.uid is not None

    def _sudo_call_kw(self, model, method_name, args, kw):
        """Override api.call_kw to pass it the model as sudo."""
        # message_post should have the public user as author if not logged in
        if method_name == 'message_post' and not self._is_logged_in():
            kw['author_id'] = request.uid or None
        return api.call_kw(model.sudo(), method_name, args, kw)

    def _sudo_load_action(self, **kw):
        action_id = kw.get('action_id')
        additional_context = kw.get('additional_context', None)

        Actions = request.env['ir.actions.actions']
        value = False
        try:
            action_id = int(action_id)
        except ValueError:
            try:
                action = request.env.ref(action_id)
                assert action._name.startswith('ir.actions.')
                action_id = action.id
            except Exception:
                action_id = 0  # force failed read

        base_action = Actions.sudo().browse([action_id]).read(['type'])
        if base_action:
            ctx = dict(request.context)
            action_type = base_action[0]['type']
            if action_type == 'ir.actions.report':
                ctx.update({'bin_size': True})
            if additional_context:
                ctx.update(additional_context)
            request.context = ctx
            action = request.env[action_type].sudo().browse([action_id]).read()
            if action:
                value = clean_action(action[0])
        return value

    def _sudo_mail_init_messaging(self):
        """This is a copy-paste of MailController.mail_init_messaging with auth='public' and request made as superuser."""
        env = request.env(user=SUPERUSER_ID)
        values = {
            'needaction_inbox_counter': env['res.partner'].get_needaction_count(),
            'starred_counter': env['res.partner'].get_starred_count(),
            'channel_slots': env['mail.channel'].channel_fetch_slot(),
            'mail_failures': env['mail.message'].message_fetch_failed(),
            'commands': env['mail.channel'].get_mention_commands(),
            'mention_partner_suggestions': env['res.partner'].get_static_mention_suggestions(),
            'shortcodes': env['mail.shortcode'].sudo().search_read([],
                                                                   ['source', 'substitution', 'description']),
            'menu_id': env['ir.model.data'].xmlid_to_res_id('mail.mail_channel_menu_root_chat'),
            'is_moderator': env.user.is_moderator,
            'moderation_counter': env.user.moderation_counter,
            'moderation_channel_ids': env.user.moderation_channel_ids.ids,
        }
        return values

    def _sudo_read(self, model, **kw):
        """Override models.read to pass it the model as sudo."""
        kwargs = {k: v for k, v in kw.items() if k in ['fields', 'load']}
        return model.sudo().read(**kwargs)

    def _sudo_read_group(self, model, **kw):
        """Override models.read_group to pass it the model as sudo."""
        domain = kw.get('domain', [])
        fields = kw.get('fields', [])
        groupby = kw.get('groupby', [])
        kwargs = {k: v for k, v in kw.items() if k in ['offset', 'limit', 'orderby', 'lazy']}
        return model.sudo().read_group(domain, fields, groupby, **kwargs)

    def _sudo_read_progress_bar(self, model, **kw):
        """Override models.read_progress_bar to pass it the model as sudo."""
        domain = kw.get('domain', [])
        group_by = kw.get('group_by', '')
        progress_bar = kw.get('progress_bar', {})
        return model.sudo().read_progress_bar(domain, group_by, progress_bar)

    def _sudo_resequence(self, model, **kw):
        """Override Dataset.resequence to pass it the model as sudo."""
        ids = kw.get('ids', [])
        kwargs = {k: v for k, v in kw.items() if k in ['fields', 'offset']}
        return DataSet.resequence(self, model.sudo(), ids, **kwargs)

    def _sudo_search_read(self, model, **kw):
        """Override models.search_read to pass it the model as sudo."""
        kwargs = {k: v for k, v in kw.items() if k in ['domain', 'fields', 'offset', 'limit', 'order']}
        model_sudo = model.sudo()
        records = model_sudo.search_read(**kwargs)

        if not records:
            return {
                'length': 0,
                'records': []
            }
        if kw.get('limit') and len(records) == kw.get('limit'):
            length = model_sudo.search_count(kw.get('domain'))
        else:
            length = len(records) + (kw.get('offset', 0))
        return {
            'length': length,
            'records': records
        }
