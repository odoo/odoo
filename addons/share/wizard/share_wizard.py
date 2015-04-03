# -*- coding: utf-8 -*-

import logging
import random
import simplejson
import time
import uuid

import openerp
from openerp import api, fields, models, tools, _
from openerp.exceptions import UserError
from openerp.osv import expression
from openerp.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

FULL_ACCESS = ('perm_read', 'perm_write', 'perm_create', 'perm_unlink')
READ_WRITE_ACCESS = ('perm_read', 'perm_write')
READ_ONLY_ACCESS = ('perm_read',)

# Pseudo-domain to represent an empty filter, constructed using
# osv.expression's DUMMY_LEAF
DOMAIN_ALL = [(1, '=', 1)]

# A good selection of easy to read password characters (e.g. no '0' vs 'O', etc.)
RANDOM_PASS_CHARACTERS = 'aaaabcdeeeefghjkmnpqrstuvwxyzAAAABCDEEEEFGHJKLMNPQRSTUVWXYZ23456789'
def generate_random_pass():
    return ''.join(random.sample(RANDOM_PASS_CHARACTERS,10))

class ShareWizard(models.TransientModel):
    _name = 'share.wizard'
    _description = 'Share Wizard'

    action_id = fields.Many2one('ir.actions.act_window', string='Action to share', required=True, default=lambda self: self.env.context.get('action_id'),
            help="The action that opens the screen containing the data you wish to share.")
    view_type = fields.Char(string='Current View Type', required=True, default='page')
    domain = fields.Char(string='Domain', help="Optional domain for further data filtering", default=lambda self: self.env.context.get('domain', '[]'))
    user_type = fields.Selection('_user_type_selection', string='Sharing method', required=True, default='embedded', 
                help="Select the type of user(s) you would like to share data with.")
    new_users = fields.Text("Emails")
    email_1 = fields.Char('New user email', size=64)
    email_2 = fields.Char('New user email', size=64)
    email_3 = fields.Char('New user email', size=64)
    invite = fields.Boolean(string='Invite users to OpenSocial record', default=True)
    access_mode = fields.Selection([('readonly','Can view'),('readwrite','Can edit')], string='Access Mode', required=True, default='readwrite',
                                    help="Access rights to be granted on the shared documents.")
    result_line_ids = fields.One2many('share.wizard.result.line', 'share_wizard_id', string='Summary', readonly=True)
    share_root_url = fields.Char(string='Share Access URL', readonly=True, compute='_compute_share_root_url',
                            help='Main access page for users that are granted shared access')
    name = fields.Char(string='Share Title', required=True, help="Title for the share (displayed to users as menu and shortcut name)")
    record_name = fields.Char(string='Record name', help="Name of the shared record, if sharing a precise record")
    message = fields.Text(string="Personal Message", help="An optional personal message, to be included in the email notification.")
    embed_code = fields.Text(string='Code', compute='_compute_embed_code',
        help="Embed this code in your documents to provide a link to the "\
              "shared document.")
    embed_option_title = fields.Boolean(string='Display title', default=True)
    embed_option_search = fields.Boolean(string='Display search view', default=True)
    embed_url = fields.Char(string='Share URL', readonly=True, compute='_compute_embed_url')

    def _user_type_selection(self):
        """Selection values may be easily overridden/extended via inheritance"""
        return [('embedded', _('Direct link or embed code')), ('emails',_('Emails')), ]

    def _compute_share_root_url(self):
        data = dict(dbname=self.env.cr.dbname, login='', password='')
        self.share_root_url = self.share_url_template() % data

    def _compute_embed_code(self):
        self.embed_code = self._generate_embedded_code()

    def _compute_embed_url(self):
        if self.result_line_ids:
            user = self.result_line_ids[0]
            data = dict(dbname=self.env.cr.dbname, login=user.login, password=user.password, action=self.action_id.id)
            self.embed_url = self.with_context(share_url_template_hash_arguments = ['action']).share_url_template() % data

    @api.onchange('embed_option_title', 'embed_option_search')
    def _onchange_embed_options(self):
        options = dict(title=self.embed_option_title, search=self.embed_option_search)
        return {'value': {'embed_code': self._generate_embedded_code(options)}}

    """Override of create() to auto-compute the action name"""
    @api.model
    def create(self, values):
        if 'action_id' in values and not 'name' in values:
            action = self.env['ir.actions.actions'].browse(values['action_id'])
            values['name'] = action.name
        return super(ShareWizard,self).create(values)

    @api.multi
    def go_step_1(self):
        self.ensure_one()
        if self.user_type == 'emails' and not self.has_email():
            raise UserError(_('You must configure your email address in the user preferences before using the Share button.'))
        res = self.env.ref('share.action_share_wizard_step1')
        action = res.read()[0]
        action['res_id'] = self.id
        action.pop('context', '')
        return action

    @api.multi
    def go_step_2(self):

        self.ensure_one()
        self._check_preconditions()

        # Create shared group and users

        group_id, new_users, existing_users = self._create_share_users_group()

        model = self.env['ir.model'].search([('model','=', self.action_id.res_model)], limit=1)

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
        obj0, obj1, obj2, obj3 = self._get_relationship_classes(model)
        mode = self.access_mode

        # Add access to [obj0] and [obj1] according to chosen mode
        self._add_access_rights_for_share_group(group_id, mode, obj0)
        self._add_access_rights_for_share_group(group_id, mode, obj1)

        # Add read-only access (always) to [obj2]
        self._add_access_rights_for_share_group(group_id, 'readonly', obj2)

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
        self._link_or_copy_current_user_rules(group_id, all_relations)
        # B.
        main_domain = self.domain if self.domain != '[]' else str(DOMAIN_ALL)
        self._create_or_combine_sharing_rule(group_id, model_id=model.id, domain=main_domain, restrict=True)
        # C.
        self._create_indirect_sharing_rules(group_id, obj1)

        # refresh wizard_data[]
        self.refresh()

        # EMAILS AND NOTIFICATIONS
        #  A. Not invite: as before
        #     -> send emails to destination users
        #  B. Invite (OpenSocial)
        #     -> subscribe all users (existing and new) to the record
        #     -> send a notification with a summary to the current record
        #     -> send a notification to all users; users allowing to receive
        #        emails in preferences will receive it
        #        new users by default receive all notifications by email

        # A.
        if not self.invite:
            self.send_emails()
        # B.
        else:
            # Invite (OpenSocial): automatically subscribe users to the record
            res_id = 0
            for cond in safe_eval(main_domain):
                if cond[0] == 'id':
                    res_id = cond[2]
            # Record id not found: issue
            if res_id <= 0:
                raise UserError(_('The share engine has not been able to fetch a record_id for your invitation.'))
            res = self.env[model.model].browse(res_id)
            res.message_subscribe(new_users + existing_users)
            # self.send_invite_email(cr, uid, wizard_data, context=context)
            # self.send_invite_note(cr, uid, model.model, res_id, wizard_data, context=context)

        # CLOSE
        #  A. Not invite: as before
        #  B. Invite: skip summary screen, get back to the record

        # A.
        if not self.invite:
            step2_form_view = self.env.ref('share.share_step2_form')
            return {
                'name': _('Shared access created!'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'share.wizard',
                'view_id': False,
                'res_id': self.id,
                'views': [(step2_form_view.id, 'form'), (False, 'tree'), (False, 'calendar'), (False, 'graph')],
                'type': 'ir.actions.act_window',
                'target': 'new'
            }
        # B.
        else:
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': model.model,
                'view_id': False,
                'res_id': res_id,
                'views': [(False, 'form'), (False, 'tree'), (False, 'calendar'), (False, 'graph')],
                'type': 'ir.actions.act_window',
            }

    def send_emails(self):
        _logger.info('Sending share notifications by email...')
        Mail = self.env['mail.mail']
        user = self.env.user
        if not user.email:
            raise UserError(_('The current user must have an email address configured in User Preferences to be able to send outgoing emails.'))

        # TODO: also send an HTML version of this mail
        mails = []
        for result_line in self.result_line_ids:
            email_to = result_line.user_id.email
            if not email_to:
                continue
            subject = self.name
            body = _("Hello,\n\n")
            body += _("I've shared %s with you!\n\n") % self.name
            body += _("The documents are not attached, you can view them online directly on my Odoo server at:\n    %s\n\n") % (result_line.share_url)
            if self.message:
                body += '%s\n\n' % (self.message)
            if result_line.newly_created:
                body += _("These are your credentials to access this protected area:\n")
                body += "%s: %s\n" % (_("Username"), result_line.user_id.login)
                body += "%s: %s\n" % (_("Password"), result_line.password)
                body += "%s: %s\n" % (_("Database"), self.env.cr.dbname)
            else:
                body += _("The documents have been automatically added to your current Odoo documents.\n")
                body += _("You may use your current login (%s) and password to view them.\n") % result_line.user_id.login
            body += "\n\n%s\n\n" % ( (user.signature or '') )
            body += "--\n"
            body += _("Odoo is a powerful and user-friendly suite of Business Applications (CRM, Sales, HR, etc.)\n"
                      "It is open source and can be found on https://www.odoo.com.")
            mails.append(Mail.create({
                    'email_from': user.email,
                    'email_to': email_to,
                    'subject': subject,
                    'body_html': '<pre>%s</pre>' % body}).send())
        # force direct delivery, as users expect instant notification
        _logger.info('%d share notification(s) sent.', len(mails))

    def has_group(self, group_xml_id):
        """Returns True if current user is a member of the group identified by the module, group_xml_id pair."""
        # if the group was deleted or does not exist, we say NO (better safe than sorry)
        try:
            group_id = self.env.ref(group_xml_id)
        except ValueError:
            return False
        return group_id in self.env.user.groups_id

    @api.one
    def has_share(self):
        return self.has_group(group_xml_id='base.group_no_one')

    def has_email(self):
        return bool(self.env.user.email)

    def share_url_template(self):

        # NOTE: take _ids in parameter to allow usage through browse_record objects
        base_url = self.env['ir.config_parameter'].get_param('web.base.url', default='')
        if base_url:
            base_url += '/login?db=%(dbname)s&login=%(login)s&key=%(password)s'
            extra = self.env.context and self.env.context.get('share_url_template_extra_arguments')
            if extra:
                base_url += '&' + '&'.join('%s=%%(%s)s' % (x,x) for x in extra)
            hash_ = self.env.context and self.env.context.get('share_url_template_hash_arguments')
            if hash_:
                base_url += '#' + '&'.join('%s=%%(%s)s' % (x,x) for x in hash_)
        return base_url

    def _assert(self, condition, error_message, context=None):
        """Raise a user error with the given message if condition is not met.
           The error_message should have been translated with _().
        """
        if not condition:
            raise UserError(error_message)

    def _generate_embedded_code(self, options=None):
        if options is None:
            options = {}

        js_options = {}
        title = options['title'] if 'title' in options else self.embed_option_title
        search = (options['search'] if 'search' in options else self.embed_option_search) if self.access_mode != 'readonly' else False

        if not title:
            js_options['display_title'] = False
        if search:
            js_options['search_view'] = True

        js_options_str = (', ' + simplejson.dumps(js_options)) if js_options else ''

        base_url = self.env['ir.config_parameter'].get_param('web.base.url', default=None)
        user = self.result_line_ids[0]

        return """
<script type="text/javascript" src="%(base_url)s/web/webclient/js"></script>
<script type="text/javascript">
    new openerp.init(%(init)s).web.embed(%(server)s, %(dbname)s, %(login)s, %(password)s,%(action)d%(options)s);
</script> """ % {
            'init': simplejson.dumps(openerp.conf.server_wide_modules),
            'base_url': base_url or '',
            'server': simplejson.dumps(base_url),
            'dbname': simplejson.dumps(self.env.cr.dbname),
            'login': simplejson.dumps(user.login),
            'password': simplejson.dumps(user.password),
            'action': user.user_id.action_id.id,
            'options': js_options_str,
        }

    def _create_share_group(self):
        share_group_name = '%s: %s (%d-%s)' %('Shared', self.name, self.env.uid, time.time())
        values = {'name': share_group_name, 'share': True}
        try:
            implied_group = self.env.ref('share.group_shared')
        except ValueError:
            implied_group = None
        if implied_group:
            values['implied_ids'] = [(4, implied_group.id)]
        # create share group without putting admin in it
        return self.env['res.groups'].sudo().with_context({'noadmin': True}).create(values).id

    def _create_new_share_users(self, group_id):
        """Create one new res.users record for each email address provided in
           wizard_data.new_users, ignoring already existing users.
           Populates wizard_data.result_line_ids with one new line for
           each user (existing or not). New users will also have a value
           for the password field, so they can receive it by email.
           Returns the ids of the created users, and the ids of the
           ignored, existing ones."""
        context = dict(self.env.context or {})
        UserObj = self.env['res.users']
        current_user = self.env.user
        # modify context to disable shortcuts when creating share users
        context['noshortcut'] = True
        context['no_reset_password'] = True
        created_users = []
        existing_users = []
        if self.user_type == 'emails':
            # get new user list from email data
            new_users = (self.new_users or '').split('\n')
            new_users += [self.email_1 or '', self.email_2 or '', self.email_3 or '']
            for new_user in new_users:
                # Ignore blank lines
                new_user = new_user.strip()
                if not new_user: continue
                # Ignore the user if it already exists.
                if not self.invite:
                    existing = UserObj.sudo().search([('login', '=', new_user)])
                else:
                    existing = UserObj.sudo().search([('email', '=', new_user)])
                existing_users.extend(existing)
                if existing:
                    new_line = { 'user_id': existing.id,
                                 'newly_created': False}
                    self.write({'result_line_ids': [(0,0,new_line)]})
                    continue
                new_pass = generate_random_pass()
                user = UserObj.sudo().with_context(context).create({
                        'login': new_user,
                        'password': new_pass,
                        'name': new_user,
                        'email': new_user,
                        'groups_id': [(6,0,[group_id])],
                        'company_id': current_user.company_id.id,
                        'company_ids': [(6, 0, [current_user.company_id.id])],
                        'share': True,
                })
                new_line = { 'user_id': user.id,
                             'password': new_pass,
                             'newly_created': True}
                self.write({'result_line_ids': [(0,0,new_line)]})
                created_users.append(user)

        elif self.user_type == 'embedded':
            new_login = 'embedded-%s' % (uuid.uuid4().hex,)
            new_pass = generate_random_pass()
            user = UserObj.sudo().with_context(context).create({
                'login': new_login,
                'password': new_pass,
                'name': new_login,
                'groups_id': [(6,0,[group_id])],
                'company_id': current_user.company_id.id,
                'company_ids': [(6, 0, [current_user.company_id.id])],
            })
            new_line = { 'user_id': user.id,
                         'password': new_pass,
                         'newly_created': True}
            self.write({'result_line_ids': [(0,0,new_line)]})
            created_users.append(user)

        return created_users, existing_users

    def _create_action(self, values):
        new_context = self.env.context.copy()
        for key in self.env.context:
            if key.startswith('default_'):
                del new_context[key]
        action = self.env['ir.actions.act_window'].sudo().with_context(new_context).create(values)
        return action

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
                _logger.debug("Failed to cleanup action context as it does not parse server-side", exc_info=True)
                result = context_str
        return result

    def _shared_action_def(self):
        copied_action = self.action_id

        if self.access_mode == 'readonly':
            view_mode = self.view_type
            view_id = copied_action.view_id.id if copied_action.view_id.type == self.view_type else False
        else:
            view_mode = copied_action.view_mode
            view_id = copied_action.view_id.id


        action_def = {
            'name': self.name,
            'domain': copied_action.domain,
            'context': self._cleanup_action_context(self.action_id.context, self._uid),
            'res_model': copied_action.res_model,
            'view_mode': view_mode,
            'view_type': copied_action.view_type,
            'search_view_id': copied_action.search_view_id.id if self.access_mode != 'readonly' else False,
            'view_id': view_id,
            'auto_search': True,
        }
        if copied_action.view_ids:
            action_def['view_ids'] = [(0,0,{'sequence': x.sequence,
                                            'view_mode': x.view_mode,
                                            'view_id': x.view_id.id })
                                      for x in copied_action.view_ids
                                      if (self.access_mode != 'readonly' or x.view_mode == self.view_type)
                                     ]
        return action_def

    def _setup_action_and_shortcut(self, user_ids, make_home):
        """Create a shortcut to reach the shared data, as well as the corresponding action, for
           each user in ``user_ids``, and assign it as their home action if ``make_home`` is True.
           Meant to be overridden for special cases.
        """
        values = self._shared_action_def()
        for user in user_ids:
            action = self.sudo(user)._create_action(values)
            if make_home:
                # We do this only for new share users, as existing ones already have their initial home
                # action. Resetting to the default menu does not work well as the menu is rather empty
                # and does not contain the shortcuts in most cases.
                user.sudo().write({'action_id': action.id})

    def _get_recursive_relations(self, model, ttypes, relation_fields=None, suffix=None):
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
        ModelObj = self.env['ir.model']
        for field in self.env[model.model]._fields.itervalues():
            ftype = field.type
            relation_field = None
            if ftype in ttypes and field.comodel_name not in models:
                relation_model = ModelObj.sudo().search([('model','=',field.comodel_name)], limit=1)
                RelationOsv = self.env[field.comodel_name]
                #skip virtual one2many fields (related, ...) as there is no reverse relationship
                if ftype == 'one2many' and field.inverse_name:
                    # don't record reverse path if it's not a real m2o (that happens, but rarely)
                    dest_fields = RelationOsv._fields
                    reverse_rel = field.inverse_name
                    if reverse_rel in dest_fields and dest_fields[reverse_rel].type == 'many2one':
                        relation_field = ('%s.%s'%(reverse_rel, suffix)) if suffix else reverse_rel
                local_rel_fields.append((relation_field, relation_model))
                for parent in RelationOsv._inherits:
                    if parent not in models:
                        ParentModel = self.env[parent]
                        parent_fields = ParentModel._fields
                        parent_model_browse = ModelObj.sudo().search([('model','=',parent)])
                        if relation_field and field.inverse_name in parent_fields:
                            # inverse relationship is available in the parent
                            local_rel_fields.append((relation_field, parent_model_browse))
                        else:
                            # TODO: can we setup a proper rule to restrict inherited models
                            # in case the parent does not contain the reverse m2o?
                            local_rel_fields.append((None, parent_model_browse))
                if relation_model.id != model.id and ftype in ['one2many', 'many2many']:
                    local_rel_fields += self._get_recursive_relations(relation_model,
                        [ftype], relation_fields + local_rel_fields, suffix=relation_field)
        return local_rel_fields

    def _get_relationship_classes(self, model):
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
        IrModelObj = self.env['ir.model']
        for parent in self.env[model.model]._inherits:
            parent_model_browse = IrModelObj.sudo().browse(IrModelObj.sudo().search([('model','=',parent)]))
            obj0 += [(None, parent_model_browse)]

        obj1 = self._get_recursive_relations(model, ['one2many'], relation_fields=obj0)
        obj2 = self._get_recursive_relations(model, ['one2many', 'many2many'], relation_fields=obj0)
        obj3 = self._get_recursive_relations(model, ['many2one'], relation_fields=obj0)
        for dummy, model in obj1:
            obj3 += self._get_recursive_relations(model, ['many2one'], relation_fields=obj0)
        return obj0, obj1, obj2, obj3

    def _get_access_map_for_groups_and_models(self, group_ids, model_ids):
        user_rights = self.env['ir.model.access'].search([('group_id', 'in', group_ids), ('model_id', 'in', model_ids)])
        user_access_matrix = {}
        if user_rights:
            for access_right in user_rights:
                access_line = user_access_matrix.setdefault(access_right.model_id.model, set())
                for perm in FULL_ACCESS:
                    if getattr(access_right, perm, 0):
                        access_line.add(perm)
        return user_access_matrix

    def _add_access_rights_for_share_group(self, group_id, mode, fields_relations):
        """Adds access rights to group_id on object models referenced in ``fields_relations``,
           intersecting with access rights of current user to avoid granting too much rights
        """
        target_model_ids = [x[1].id for x in fields_relations]
        perms_to_add = (mode == 'readonly') and READ_ONLY_ACCESS or READ_WRITE_ACCESS
        current_user = self.env.user

        current_user_access_map = self._get_access_map_for_groups_and_models(
            [x.id for x in current_user.groups_id], target_model_ids)
        group_access_map = self._get_access_map_for_groups_and_models(
            [group_id], target_model_ids)
        _logger.debug("Current user access matrix: %r", current_user_access_map)
        _logger.debug("New group current access matrix: %r", group_access_map)

        # Create required rights if allowed by current user rights and not
        # already granted
        for dummy, model in fields_relations:
            # mail.message is transversal: it should not received directly the access rights
            if model.model in ['mail.message', 'mail.notification']: continue
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
                self.env['ir.model.access'].sudo().create(values)
                _logger.debug("Creating access right for model %s with values: %r", model.model, values)

    def _link_or_copy_current_user_rules(self, group_id, fields_relations):
        rules_done = set()
        for group in self.env.user.groups_id:
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
                            rule.sudo().copy(default={
                                'name': '%s %s' %(rule.name, _('(Copy for sharing)')),
                                'groups': [(6,0,[group_id])],
                                'domain_force': rule.domain, # evaluated version!
                            })
                            _logger.debug("Copying rule %s (%s) on model %s with domain: %s", rule.name, rule.id, model.model, rule.domain_force)
                        else:
                            # otherwise we can simply link the rule to keep it dynamic
                            rule.sudo().write({
                                    'groups': [(4,group_id)]
                                })
                            _logger.debug("Linking rule %s (%s) on model %s with domain: %s", rule.name, rule.id, model.model, rule.domain_force)

    def _check_personal_rule_or_duplicate(self, group_id, rule):
        """Verifies that the given rule only belongs to the given group_id, otherwise
           duplicate it for the current group, and unlink the previous one.
           The duplicated rule has the original domain copied verbatim, without
           any evaluation.
           Returns the final rule to use (browse_record), either the original one if it
           only belongs to this group, or the copy."""
        if len(rule.groups) == 1:
            return rule
        # duplicate it first:

        new_id = rule.sudo().copy(default={
                                       'name': '%s %s' %(rule.name, _('(Duplicated for modified sharing permissions)')),
                                       'groups': [(6,0,[group_id])],
                                       'domain_force': rule.domain_force, # non evaluated!
                               })
        _logger.debug("Duplicating rule %s (%s) (domain: %s) for modified access ", rule.name, rule.id, rule.domain_force)
        # then disconnect from group_id:
        rule.write({'groups':[(3,group_id)]}) # disconnects, does not delete!
        return new_id

    def _create_or_combine_sharing_rule(self, group_id, model_id, domain, restrict=False, rule_name=None):
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
                            (self.env.user.name, self.env.user.login, group_id)
        RuleObj = self.env['ir.rule']
        rules = RuleObj.sudo().search([('groups', 'in', group_id), ('model_id', '=', model_id)])
        if rules:
            for rule in rules:
                if rule.domain_force == domain:
                    # don't create it twice!
                    if restrict:
                        continue
                    else:
                        _logger.debug("Ignoring sharing rule on model %s with domain: %s the same rule exists already", model_id, domain)
                        return
                if restrict:
                    # restricting existing rules is done by adding the clause
                    # with an AND, but we can't alter the rule if it belongs to
                    # other groups, so we duplicate if needed
                    rule = self._check_personal_rule_or_duplicate(group_id, rule)
                    eval_ctx = RuleObj._eval_context_for_combinations()
                    org_domain = expression.normalize_domain(eval(rule.domain_force, eval_ctx))
                    new_clause = expression.normalize_domain(eval(domain, eval_ctx))
                    combined_domain = expression.AND([new_clause, org_domain])
                    rule.write({'domain_force': combined_domain, 'name': rule.name + _('(Modified)')})
                    _logger.debug("Combining sharing rule %s on model %s with domain: %s", rule.id, model_id, domain)
        if not rules or not restrict:
            # Adding the new rule in the group is ok for normal cases, because rules
            # in the same group and for the same model will be combined with OR
            # (as of v6.1), so the desired effect is achieved.
            RuleObj.sudo().create({
                'name': rule_name,
                'model_id': model_id,
                'domain_force': domain,
                'groups': [(4,group_id)]
                })
            _logger.debug("Created sharing rule on model %s with domain: %s", model_id, domain)

    def _create_indirect_sharing_rules(self, group_id, fields_relations):
        rule_name = _('Indirect sharing filter created by user %s (%s) for group %s') % \
                            (self.env.user.name, self.env.user.login, group_id)
        try:
            domain = safe_eval(self.domain)
            if domain:
                for rel_field, model in fields_relations:
                    # mail.message is transversal: it should not received directly the access rights
                    if model.model in ['mail.message', 'mail.notification']: continue
                    related_domain = []
                    if not rel_field: continue
                    for element in domain:
                        if expression.is_leaf(element):
                            left, operator, right = element
                            left = '%s.%s'%(rel_field, left)
                            element = left, operator, right
                        related_domain.append(element)
                    self._create_or_combine_sharing_rule(group_id, model_id=model.id, domain=str(related_domain),
                         rule_name=rule_name, restrict=True)
        except Exception:
            _logger.info('Failed to create share access', exc_info=True)
            raise UserError(_('Sorry, the current screen and filter you are trying to share are not supported at the moment.\nYou may want to try a simpler filter.'))

    def _check_preconditions(self):
        self._assert(self.action_id and self.access_mode,
                     _('Action and Access Mode are required to create a shared access.'))
        self._assert(self.has_share(),
                     _('You must be a member of the Technical group to use the share wizard.'))
        if self.user_type == 'emails':
            self._assert((self.new_users or self.email_1 or self.email_2 or self.email_3),
                     _('Please indicate the emails of the persons to share with, one per line.'))

    def _create_share_users_group(self):
        """Creates the appropriate share group and share users, and populates
           result_line_ids of wizard_data with one line for each user.

           :return: a tuple composed of the new group id (to which the shared access should be granted),
                the ids of the new share users that have been created and the ids of the existing share users
        """
        group_id = self._create_share_group()
        # First create any missing user, based on the email addresses provided
        new_users, existing_users = self._create_new_share_users(group_id)
        # Finally, setup the new action and shortcut for the users.
        if existing_users:
            # existing users still need to join the new group
            for existing in existing_users:
                existing.sudo().write({'groups_id': [(4,group_id)]})
            # existing user don't need their home action replaced, only a new shortcut
            self._setup_action_and_shortcut(existing_users, make_home=False)
        if new_users:
            # new users need a new shortcut AND a home action
            self._setup_action_and_shortcut(new_users, make_home=True)
        return group_id, new_users, existing_users

class ShareResultLine(models.TransientModel):
    _name = 'share.wizard.result.line'
    _rec_name = 'user_id'

    user_id = fields.Many2one('res.users', required=True, readonly=True)
    login = fields.Char(string='Login', related='user_id.login', required=True, readonly=True)
    password = fields.Char(string='Password', readonly=True)
    share_url = fields.Char(string='Share URL', compute='_compute_share_url')
    share_wizard_id = fields.Many2one('share.wizard', string='Share Wizard', required=True, ondelete='cascade')
    newly_created = fields.Boolean(string='Newly created', readonly=True, default=True)

    def _compute_share_url(self):
        for this in self:
            data = dict(dbname=this.env.cr.dbname, login=this.login, password=this.password)
            if this.share_wizard_id and this.share_wizard_id.action_id:
                data['action'] = this.share_wizard_id.action_id.id
                this.share_url = this.share_wizard_id.with_context(share_url_template_hash_arguments = ['action']).share_url_template() % data
