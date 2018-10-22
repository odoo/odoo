# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import functools
from odoo import api, http, SUPERUSER_ID, _
from odoo.addons.web.controllers.main import clean_action, DataSet
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import consteq


class PublicProject(http.Controller):

    # ROUTES

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

    # DECORATORS

    def chatter_track(operation):
        """Prepare values for chatter tracking, then call the decorated function, then track for chatter.

        :param operation: (str) 'read', 'write' or 'create' (note: fields to track are defined in function
                                of that operation type, via self._tracked_fields(operation)).
        """
        def decorator(f):
            @functools.wraps(f)
            def response_wrap(self, *args, **kw):
                fields = self._tracked_fields(operation)

                task = request.env['project.task']
                task = task.sudo() if not self._is_logged_in() else task

                if operation == 'write' and args[0]:
                    task = task.browse(args[0])
                    tracked_fields = task.fields_get(fields) if task else None
                    initial_values = dict([(task.id, {field: task[field] for field in fields})])

                response = f(self, *args, **kw)

                # If we're creating a task, we only get the task's id after creating it
                # The initial values are pre-creation of the task so by definition they're all None
                if operation == 'create' and response:
                    task = task.browse(response)
                    tracked_fields = task.fields_get(fields) if task else None
                    initial_values = dict([(task.id, {field: None for field in fields})])

                if task and initial_values and tracked_fields:
                    author_id = request.env.uid if not self._is_logged_in() else None
                    task.message_track(tracked_fields, initial_values, author_id=author_id)
                return response
            return response_wrap
        return decorator
    
    def verify_and_dispatch(method_to_call):
        def decorator(f):
            @functools.wraps(f)
            def response_wrap(self, *args, **kw):
                is_logged_in = self._is_logged_in()
                access_info = kw.pop('access_info')
                submethod = kw.get('method')

                access_token = access_info.pop('access_token')
                project_id = access_info.get('project_id')
                task_id = access_info.get('task_id')

                # 1. Get operation type ('read', 'write', 'create') of the method
                operation = self._check_operation(submethod if method_to_call in ['call', 'call_kw'] else method_to_call)

                # 2. Check token and whitelists
                if operation and access_token:
                    action = 'edit' if operation in ['write', 'create'] else 'read'
                    has_access = self.check_access(access_token,
                                                   project_id=project_id,
                                                   task_id=task_id if operation != 'create' else None,
                                                   action=action)
                    model = kw.get('model')
                    fields = kw.get('kwargs', {}).get('fields', [])
                    domain = kw.get('kwargs', {}).get('domain', [])

                    # `BaseModel.read()` passes the fields as args[1]
                    if submethod == 'read':
                        fields = kw.get('args')[1]
                        # `BaseModel.read()` defaults with *all fields* if no fields are passed.
                        if not fields:
                            raise AccessError(_("Forbidden to read all fields on this model."))
                    # BaseModel.default_get() and .create() pass the fields as args[0]
                    elif submethod in ['default_get', 'create']:
                        fields = kw.get('args')[0]
                    
                    is_whitelisted = self._check_whitelists(operation, model, fields, domain)

                    if has_access and is_whitelisted:
                        if method_to_call in ['call', 'call_kw']:
                            return f(self, operation, task_id, *args, **kw)
                        if method_to_call == 'resequence':
                            return f(self, task_id, *args, **kw)
                        return f(self, *args, **kw)
                
                # 3. Or revert to regular perm checks for user
                if is_logged_in:
                    mtc = 'load' if method_to_call == 'load_action' else method_to_call
                    return getattr(self, mtc)(**kw)
                
                # If [no valid token or operation not whitelisted]
                # and user is not logged in:
                raise AccessError(_("Access denied."))
            return response_wrap
        return decorator

    # PRIVATE METHODS

    def _check_operation(self, method):
        wl = self._whitelist()
        for op_name in wl:
            op = wl.get(op_name)
            if method in op['all']['methods']:
                return op_name
            for model in op:
                if method in op.get(model)['methods']:
                    return op_name
        return

    def _check_whitelists(self, operation, model, fields, domain):
        if model:
            # 1. Check the model access (for that operation)
            if not self._is_whitelisted(operation, model=model):
                return
            # 2. Check the fields access (for that operation on that model)
            for field in fields:
                if not self._is_whitelisted(operation, model=model, field=field):
                    return

        # 3. Check the domain (for that operation on that model)
        for d in domain:
            if not isinstance(d, str):
                # d[0] is a field name
                is_field_ok = self._is_whitelisted(operation, model=model, field=d[0])
                if not is_field_ok:
                    return
        
        return True
    
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

    def _is_whitelisted(self, operations, method=None, model=None, field=None):
        # Can't have method AND field (makes no sense anyway)
        operations = [operations] if isinstance(operations, str) else operations
        whitelist = self._whitelist()
        for op in operations:
            wl = whitelist.get(op)
            if field:
                if field in wl['all']['fields'] or model and field in wl.get(model)['fields']:
                    return op
            elif method:
                if method in wl['all']['methods'] or model and method in wl.get(model)['methods']:
                    return op
            elif model:
                if model in wl:
                    return op
        return False

    def _sudo_call_kw(self, model, method_name, args, kw):
        """Override api.call_kw to pass it the model as sudo."""
        # message_post should have the public user as author if not logged in
        if method_name == 'message_post' and not self._is_logged_in():
            kw['author_id'] = request.uid or None
        return api.call_kw(model.sudo(), method_name, args, kw)

    @chatter_track('create')
    def _sudo_call_kw_create(self, model, method_name, args, kw):
        return self._sudo_call_kw(model, method_name, args, kw)
    
    def _sudo_call_kw_read(self, model, method_name, args, kw):
        return self._sudo_call_kw(model, method_name, args, kw)
    
    @chatter_track('write')
    def _sudo_call_kw_write(self, task_id, model, method_name, args, kw):
        return self._sudo_call_kw(model, method_name, args, kw)

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

    @chatter_track('write')
    def _sudo_resequence(self, model, **kw):
        """Override BaseModel.resequence to pass it the model as sudo."""
        ids = kw.get('ids', [])
        return model.sudo().resequence(ids, offset=kw.get('offset', 0))

    def _sudo_search_read(self, model, **kw):
        """Override models.search_read to pass it the model as sudo."""
        kwargs = {k: v for k, v in kw.items() if k in ['domain', 'fields', 'offset', 'limit', 'order']}
        return DataSet.do_search_read(self, model.sudo(), **kwargs)

    def _tracked_fields(self, operation):
        if operation == 'create':
            return ['project_id', 'name', 'kanban_stage', 'stage_id']
        if operation == 'read':
            return []
        if operation == 'write':
            return ['kanban_state_label', 'stage_id', 'priority']

    def _whitelist(self):
        # operation.model.list_name.values
        # operation.all.list_name.values show methods and fields that are ok across fields and methods
        # list_name is methods or fields
        return {
            'create': {
                'all': {
                    'fields': [],
                    'methods': [],
                },
                'project.task': {
                    'fields': ['name'],
                    'methods': ['create'],
                },
            },
            'read': {
                'all': {
                    'fields': [],
                    'methods': ['load_action',
                                'mail_init_messaging'],
                },
                'project.project': {
                    'fields': [],
                    'methods': ['name_get'],
                },
                'project.task': {
                    'fields': [
                        'color',
                        'priority',
                        'stage_id',
                        'user_id', # keep ?
                        'user_email', # keep ?
                        'description',
                        'sequence',
                        'date_deadline',
                        'message_needaction_counter',
                        'attachment_ids',
                        'displayed_image_id',
                        'active',
                        'legend_blocked',
                        'legend_normal',
                        'legend_done',
                        'activity_ids',
                        'activity_state',
                        'rating_last_value',
                        'rating_ids',
                        'name',
                        'project_id',
                        'email_from',
                        'tag_ids',
                        'kanban_state', # only for kanban
                        # only for form:
                        'subtask_count',
                        'rating_count',
                        'partner_id',
                        'email_cc',
                        'parent_id',
                        'child_ids',
                        'subtask_project_id',
                        'company_id',
                        'date_assign',
                        'date_last_stage_update',
                        'working_hours_open',
                        'working_days_open',
                        'working_hours_close',
                        'working_days_close',
                        'message_ids',
                        'message_attachment_count',
                        'display_name',
                    ],
                    'methods': ['default_get',
                                'load_views',
                                'message_get_suggested_recipients',
                                'message_post', # technically a 'write' method but we want to use the chatter in readonly
                                'read',
                                'read_group',
                                'read_progress_bar',
                                'search_read'],
                },
                'project.task.type': {
                    'fields': ['display_name',
                               'description',
                               'legend_priority',
                               'id',
                               'fold',
                               'project_ids'],
                    'methods': ['read',
                                'search_read',
                                'name_get'],
                },
                'project.tags': {
                    'fields': ['display_name',
                               'color'],
                    'methods': ['read'],
                },
                'ir.ui.view': {
                    'fields': [],
                    'methods': ['get_view_id'],
                },
                'mail.message': {
                    'fields': [],
                    'methods': ['message_format',
                                'toggle_message_starred'],
                },
                'mail.channel': {
                    'fields': [],
                    'methods': ['channel_join_and_get_info'],
                },
            },
            'write': {
                'all': {
                    'fields': [],
                    'methods': [],
                },
                'project.task': {
                    'fields': ['priority',
                               'kanban_state',
                               'stage_id'],
                    'methods': ['write',
                                'onchange',
                                'resequence'],
                },
                'project.task.type': {
                    'fields': ['stage_id'],
                    'methods': ['resequence'],
                },
            },
        }
