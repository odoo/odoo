# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
import logging

from odoo import api, models, fields, _
from odoo.osv import expression
from odoo.exceptions import ValidationError, UserError
from collections import defaultdict


_logger = logging.getLogger(__name__)


class StudioApprovalRule(models.Model):
    _name = "studio.approval.rule"
    _description = "Studio Approval Rule"
    _inherit = ["studio.mixin"]

    def _default_group_id(self):
        return self.env.ref('base.group_user')

    active = fields.Boolean(default=True)
    group_id = fields.Many2one("res.groups", string="Allowed Group", required=True,
                               ondelete="cascade", default=lambda s: s._default_group_id())
    model_id = fields.Many2one("ir.model", string="Model", ondelete="cascade", required=True)
    method = fields.Char(string="Method")
    action_id = fields.Many2one("ir.actions.actions", string="Action", ondelete="cascade")
    name = fields.Char()
    message = fields.Char(translate=True, string="Description", help="This message will be displayed to users that cannot proceed without this approval")
    responsible_id = fields.Many2one("res.users", string="Responsible", help="An activity will be assigned to this user when an approval is requested")
    users_to_notify = fields.Many2many(
        comodel_name='res.users',
        string='Users to notify',
        help="These users will receive a notification via internal note when an approval is requested"
    )
    notification_order = fields.Selection(
        [('1', '1'), ('2', '2'), ('3', '3')],
        default='1',
        help="Use this field to setup multi-level validation. Next activities and notifications for an approval request will only be sent once rules from previous levels have been validated"
    )
    exclusive_user = fields.Boolean(string="Exclusive approval",
                                           help="If set, the user who approves this rule will not "
                                                "be able to approve other rules for the same "
                                                "record")
    # store these for performance reasons, reading should be fast while writing can be slower
    model_name = fields.Char(string="Model Name", related="model_id.model", store=True, index=True)
    domain = fields.Char(help="If set, the rule will only apply on records that match the domain.")
    conditional = fields.Boolean(compute="_compute_conditional", string="Conditional Rule")
    can_validate = fields.Boolean(string="Can be approved",
                                  help="Whether the rule can be approved by the current user",
                                  compute="_compute_can_validate")
    entry_ids = fields.One2many('studio.approval.entry', 'rule_id', string='Entries')
    entries_count = fields.Integer('Number of Entries', compute='_compute_entries_count')

    _sql_constraints = [
        ('method_or_action_together',
         'CHECK(method IS NULL OR action_id IS NULL)',
         'A rule must apply to an action or a method (but not both).'),
        ('method_or_action_not_null',
         'CHECK(method IS NOT NULL OR action_id IS NOT NULL)',
         'A rule must apply to an action or a method.'),
    ]

    @api.constrains("group_id")
    def _check_group_xmlid(self):
        group_xmlids = self.group_id.get_external_id()
        for rule in self:
            if not group_xmlids.get(rule.group_id.id):
                raise ValidationError(_('Groups used in approval rules must have an external identifier.'))

    @api.constrains("model_id", "method")
    def _check_model_method(self):
        for rule in self:
            if rule.model_id and rule.method:
                if rule.model_id.model == self._name:
                    raise ValidationError(_("You just like to break things, don't you?"))
                if rule.method.startswith("_") or '__' in rule.method:
                    raise ValidationError(_("Private methods cannot be restricted (since they "
                                            "cannot be called remotely, this would be useless)."))
                model = rule.model_id and self.env[rule.model_id.model]
                if not hasattr(model, rule.method) or not callable(getattr(model, rule.method)):
                    raise ValidationError(
                        _("There is no method %s on the model %s (%s)",
                        rule.method, rule.model_id.name, rule.model_id.model)
                    )
                if rule.method in ["create", "write", "unlink"]:
                    # base_automation and studio_approval executes delattr command in their
                    # unregister_hook before re-patching in their register_hook.
                    # However base_automation will not re-patch approvals and vice versa.

                    raise ValidationError(_("For compatibility purpose with base_automation,"
                                            "approvals on 'create', 'write' and 'unlink' methods "
                                            "are forbidden."))

    def write(self, vals):
        write_readonly_fields = bool(set(vals.keys()) & {'group_id', 'model_id', 'method', 'action_id'})
        if write_readonly_fields and any(rule.entry_ids for rule in self):
            raise UserError(_(
                "Rules with existing entries cannot be modified since it would break existing "
                "approval entries. You should archive the rule and create a new one instead."))
        res = super().write(vals)
        self._update_registry()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        entries = super().create(vals_list)
        self._update_registry()
        return entries

    def _update_registry(self):
        """ Update the registry after a modification on approval rules. """
        if self.env.registry.ready:
            # re-install the model patches, and notify other workers
            self._unregister_hook()
            self._register_hook()
            self.env.registry.registry_invalidated = True

    def _register_hook(self):
        """ Patch methods that should verify the approval rules """

        def _patch(model, method_name, function):
            """ Patch method `name` on `model`, unless it has been patched already. """
            if method_name.startswith("_") or '__' in method_name:
                raise ValidationError(_("Can't patch private methods."))
            if method_name in ["create", "write", "unlink"]:
                raise ValidationError(_("Can't patch 'create', 'write' and 'unlink'."))
            if model not in patched_models[method_name]:
                patched_models[method_name].add(model)
                ModelClass = model.env.registry[model._name]
                method = getattr(ModelClass, method_name, None)
                if method:
                    function.studio_approval_rule_origin = method
                    setattr(ModelClass, method_name, function)

        def _make_approval_method(method_name, model_name):
            """ Instanciate a method that verify the approval rule """
            def method(self, *args, **kwargs):
                if self.env.su:
                    # in a sudoed environment, approvals are skipped
                    # otherwise we risk breaking some important flows
                    # (e.g. ecommerce order confirmations, invoice posting because
                    # online payment succeeeded, etc.)
                    _logger.info("Skipping approval checks in a sudoed environment: method call %s ALLOWED on records %s", method_name, self)
                    return method.studio_approval_rule_origin(self, *args, **kwargs)
                approved, rules, entries = [], [], []
                approved_records = self.env[self._name]
                for record in self:
                    result = self.env['studio.approval.rule'].check_approval(model_name, record.id, method_name, None)
                    approved.append(result['approved'])
                    rules.append(result['rules'])
                    entries.append(result['entries'])
                    if result['approved']:
                        approved_records |= record

                if all(approved):
                    return method.studio_approval_rule_origin(self, *args, **kwargs)
                else:
                    unapproved_records = self - approved_records
                    msg, log_args = "Approval checks failed: method call %s REJECTED on records %s", (method_name, unapproved_records)
                    if approved_records:
                        msg += " (some records were ALLOWED for the same call: %s)"
                        log_args = (*log_args, approved_records)
                    _logger.info(msg, *log_args)
                    if len(approved_records) > 0:
                        method.studio_approval_rule_origin(approved_records, *args, **kwargs)
                    message = ''
                    title = ''
                    if len(self) > 1:
                        title = _('Approvals missing')
                        message = _('Some records were skipped because approvals were missing to\
                                    proceed with your request: ')
                        message += ', '.join(unapproved_records.mapped('display_name'))
                    else:
                        title = _('The following approvals are missing:')
                        missing_approvals = self.env['studio.approval.rule'].get_missing_approvals(rules[0], entries[0])
                        message += ', '.join([approval['message'] or approval['group_id'][1] for approval in missing_approvals])

                    return  {
                        'type': 'ir.actions.client',
                        'tag': "display_notification",
                        'params' : {
                            'title': title,
                            'message': message,
                            'sticky': False,
                            'type': 'warning',
                            'next': {
                                'type': 'ir.actions.act_window_close',
                            }
                        }
                    }

            return method

        patched_models = defaultdict(set)
        # retrieve all approvals, and patch their corresponding model
        for approval in self.search([]):
            Model = self.env.get(approval.model_name)
            if approval.method and Model is not None:
                approval_method = _make_approval_method(approval.method, approval.model_name)
                _patch(Model, approval.method, approval_method)

    def _unregister_hook(self):
        """ Remove the patches installed by _register_hook() """

        # prepare a dictionary with the model name as a key and methods list as value
        model_methods_dict = {}
        # Also take inactive rule into account in case of a write
        for rule in self.with_context(active_test=False).search([('method', '!=', False)]):
            if rule.model_name in model_methods_dict:
                model_methods_dict[rule.model_name].append(rule.method)
            else:
                model_methods_dict[rule.model_name] = [rule.method]

        # for each model, remove studio_approval patches
        for Model in self.env.registry.values():
            if Model._name in model_methods_dict:
                for method_name in model_methods_dict[Model._name]:
                    method = getattr(Model, method_name, None)
                    if method and callable(method) and hasattr(method, 'studio_approval_rule_origin'):
                        delattr(Model, method_name)

    def get_missing_approvals(self, rules, entries):
        missing_approvals = []
        done_approvals = [entry['rule_id'][0] for entry in \
                          filter(lambda entry: bool(entry['approved']), entries)]
        for rule in rules:
            if (rule['id'] not in done_approvals):
                missing_approvals.append(rule)

        return missing_approvals

    @api.constrains('responsible_id', 'group_id')
    def _constraint_user_has_group(self):
        if self.responsible_id and not self.group_id in self.responsible_id.groups_id:
            raise ValidationError(_('User is not a member of the selected group.'))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_existing_entries(self):
        if any(rule.entry_ids for rule in self):
            raise UserError(_(
                "Rules with existing entries cannot be deleted since it would delete existing "
                "approval entries. You should archive the rule instead."))

    @api.depends("group_id")
    @api.depends_context("uid")
    def _compute_can_validate(self):
        group_xmlids = self.group_id.get_external_id()
        for rule in self:
            rule.can_validate = self.env.user.has_group(group_xmlids[rule.group_id.id])

    @api.depends("domain")
    def _compute_conditional(self):
        for rule in self:
            rule.conditional = bool(rule.domain)

    @api.depends('entry_ids')
    def _compute_entries_count(self):
        for rule in self:
            rule.entries_count = len(rule.entry_ids)

    @api.model
    def create_rule(self, model, method, action_id, rule_string):
        model = self.env['ir.model']._get(model)
        return self.create({
            'model_id': model.id,
            'method': method,
            'action_id': action_id and int(action_id),
            'name': _('%(rule_string)s (%(model_name)s)', rule_string=rule_string, model_name=model.name or model.id),
        })

    def set_approval(self, res_id, approved):
        """Set an approval entry for the current rule and specified record.

        Check _set_approval for implementation details.

        :param record self: a recordset of a *single* rule (ensure_one)
        :param int res_id: ID of the record on which the approval will be set
                           (the model comes from the rule itself)
        :param bool approved: whether the rule is approved or rejected
        :return: True if the rule was approved, False if it was rejected
        :rtype: boolean
        :raise: odoo.exceptions.AccessError when the user does not have write
                access to the underlying record
        :raise: odoo.exceptions.UserError when any of the other checks failed
        """
        self.ensure_one()
        entry = self._set_approval(res_id, approved)
        return entry and entry.approved

    def delete_approval(self, res_id):
        """Delete an approval entry for the current rule and specified record.

        :param record self: a recordset of a *single* rule (ensure_one)
        :param int res_id: ID of the record on which the approval will be set
                           (the model comes from the rule itself)
        :return: True
        :rtype: boolean
        :raise: odoo.exceptions.AccessError when the user does not have write
                access to the underlying record
        :raise: odoo.exceptions.UserError when any there is no existing entry
                to cancel or when the user is trying to cancel an entry that
                they didn't create themselves
        """
        self.ensure_one()
        record = self.env[self.sudo().model_name].browse(res_id)
        record.check_access_rights('write')
        record.check_access_rule('write')
        ruleSudo = self.sudo()
        existing_entry = self.env['studio.approval.entry'].search([
                ('model', '=', ruleSudo.model_name),
                ('method', '=', ruleSudo.method), ('action_id', '=', ruleSudo.action_id.id),
                ('res_id', '=', res_id), ('rule_id', '=', self.id)])
        if existing_entry and existing_entry.user_id != self.env.user:
            # this should normally not happen because of ir.rules, but let's be careful
            # when dealing with security
            raise UserError(_("You cannot cancel an approval you didn't set yourself."))
        if not existing_entry:
            raise UserError(_("No approval found for this rule, record and user combination."))
        return existing_entry.unlink()

    def _set_approval(self, res_id, approved):
        """Create an entry for an approval rule after checking if it is allowed.

        To know if the entry can be created, checks are done in that order:
            - user has write access on the underlying record
            - user has the group required by the rule
            - there is no existing entry for that rule and record
            - if this rule has 'exclusive_user' enabled: no other
              rule has been approved/rejected for the same record
            - if this rule has 'exclusive_user' disabled: no
              rule with 'exclusive_user' enabled/disabled has been
              approved/rejected for the same record

        If all these checks pass, create an entry for the current rule with
        `approve` as its value.

        :param record self: a recordset of a *single* rule (ensure_one)
        :param int res_id: ID of the record on which the approval will be set
                           (the model comes from the rule itself)
        :param bool approved: whether the rule is approved or rejected
        :return: a new approval entry
        :rtype: :class:`~odoo.addons.web_studio.models.StudioApprovalEntry`
        :raise: odoo.exceptions.AccessError when the user does not have write
                access to the underlying record
        :raise: odoo.exceptions.UserError when any of the other checks failed
        """
        self.ensure_one()
        self = self._clean_context()
        # acquire a lock on similar rules to prevent race conditions that could bypass
        # the 'force different users' field; will be released at the end of the transaction
        ruleSudo = self.sudo()
        domain = self._get_rule_domain(ruleSudo.model_name, ruleSudo.method, ruleSudo.action_id)
        all_rule_ids = tuple(ruleSudo.search(domain).ids)
        self.env.cr.execute('SELECT id FROM studio_approval_rule WHERE id IN %s FOR UPDATE NOWAIT', (all_rule_ids,))
        # NOTE: despite the 'NOWAIT' modifier, the query will actually be retried by
        # Odoo itself (not PG); the NOWAIT ensures that no deadlock will happen
        # check if the user has write access to the record
        record = self.env[self.sudo().model_name].browse(res_id)
        record.check_access_rights('write')
        record.check_access_rule('write')
        # check if the user has the necessary group
        if not self.can_validate:
            raise UserError(_('Only %s members can approve this rule.', self.group_id.display_name))
        # check if there's an entry for this rule already
        # done in sudo since entries by other users are not visible otherwise
        existing_entry = ruleSudo.env['studio.approval.entry'].search([
            ('rule_id', '=', self.id), ('res_id', '=', res_id)
        ])
        if existing_entry:
            raise UserError(_('This rule has already been approved/rejected.'))
        # if exclusive_user on: check if another rule for the same record
        # has been approved/reject by the same user
        rule_limitation_msg = _("This approval or the one you already submitted limits you "
                                "to a single approval on this action.\nAnother user is required "
                                "to further approve this action.")
        if ruleSudo.exclusive_user:
            existing_entry = ruleSudo.env['studio.approval.entry'].search([
                ('model', '=', ruleSudo.model_name), ('res_id', '=', res_id),
                ('method', '=', ruleSudo.method), ('action_id', '=', ruleSudo.action_id.id),
                ('user_id', '=', self.env.user.id),
                ('rule_id.active', '=', True),  # archived rules should have no impact
            ])
            if existing_entry:
                raise UserError(rule_limitation_msg)
        # if exclusive_user off: check if another rule with that flag on has already been
        # approved/rejected by the same user
        if not ruleSudo.exclusive_user:
            existing_entry = ruleSudo.env['studio.approval.entry'].search([
                ('model', '=', ruleSudo.model_name), ('res_id', '=', res_id),
                ('method', '=', ruleSudo.method), ('action_id', '=', ruleSudo.action_id.id),
                ('user_id', '=', self.env.user.id), ('rule_id.exclusive_user', '=', True),
                ('rule_id.active', '=', True),  # archived rules should have no impact
            ])
            if existing_entry:
                raise UserError(rule_limitation_msg)
        # all checks passed: create the entry
        result = ruleSudo.env['studio.approval.entry'].create({
            'user_id': self.env.uid,
            'rule_id': ruleSudo.id,
            'res_id': res_id,
            'approved': approved,
        })
        if not self.env.context.get('prevent_approval_request_unlink'):
            ruleSudo._unlink_request(res_id)

        if ruleSudo.notification_order != '3':
            same_level_rules = []
            higher_level_rules = []
            # approval rules for higher levels can be requested if no rules with the current level are set
            for rule in ruleSudo.search_read([
                ('notification_order', '>=', ruleSudo.notification_order),
                ('active', '=', True),
                ("model_name", "=", ruleSudo.model_name),
                ('method', '=', ruleSudo.method),
                ('action_id', '=', ruleSudo.action_id.id)
            ], ["domain", "notification_order"]):
                if rule["id"] == ruleSudo.id:
                    continue
                rule_domain = rule["domain"] and literal_eval(rule["domain"])
                if rule_domain and not record.filtered_domain(rule_domain):
                    continue
                if rule["notification_order"] == ruleSudo.notification_order:
                    same_level_rules.append(rule["id"])
                else:
                    higher_level_rules.append(rule["id"])

            if not same_level_rules:
                for rule in ruleSudo.browse(higher_level_rules):
                    rule._create_request(res_id)
        return result

    def _get_rule_domain(self, model, method, action_id):
        # just in case someone didn't cast it properly client side, would be
        # a shame to be able to skip this 'security' because of a missing parseInt 😜
        action_id = action_id and int(action_id)
        domain = [('model_name', '=', model)]
        if method:
            domain = expression.AND([domain, [('method', '=', method)]])
        if action_id:
            domain = expression.AND([domain, [('action_id', '=', action_id)]])
        return domain

    def _clean_context(self):
        """Remove `active_test` from the context, if present."""
        # we *never* want archived rules to be applied, ensure a clean context
        if 'active_test' in self._context:
            new_ctx = self._context.copy()
            new_ctx.pop('active_test')
            self = self.with_context(new_ctx)
        return self

    @api.model
    def get_approval_spec(self, model, method, action_id, res_id=False):
        """Get the approval spec for a specific button and a specific record.

        An approval spec is a dict containing information regarding approval rules
        and approval entries for the action described with the model/method/action_id
        arguments (method and action_id cannot be truthy at the same time).

        The `rules` entry of the returned dict contains a description of the approval rules
        for the current record: the group required for its approval, the message describing
        the reason for the rule to exist, whether it can be approved if other rules for the
        same record have been approved by the same user, a domain (if the rule is conditional)
        and a computed 'can_validate' field which specifies whether the current user is in the
        required group to approve the rule. This entry contains a read_group result on the
        rule model for the fields 'group_id', 'message', 'exclusive_user', 'domain' and
        'can_validate'.

        The `entries` entry of the returned dict contains a description of the existing approval
        entries for the current record. It is the result of a read_group on the approval entry model
        for the rules found for the current record for the fields 'approved', 'user_id', 'write_date',
        'rule_id', 'model' and 'res_id'.

        If res_id is provided, domain on rules are checked against the specified record and are only
        included in the result if the record matches the domain. If no res_id is provided, domains
        are not checked and the full set of rules is returned; this is useful when editing the rules
        through Studio as you always want a full description of the rules regardless of the record
        visible in the view while you edit them.

        :param str model: technical name of the model for the requested spec
        :param str method: method for the spec
        :param int action_id: database ID of the ir.actions.action record for the spec
        :param int res_id: database ID of the record for which the spec must be checked
            Defaults to False
        :return: a dict describing the rules for the specified action and existing entries for the
                 current record and applicable rules found
        :rtype dict:
        :raise: UserError if action_id and method are both truthy (rules can only apply to a method
                or an action, not both)
        :raise: AccessError if the user does not have read access to the underlying model (and record
                if res_id is specified)
        """
        self = self._clean_context()
        if method and action_id:
            raise UserError(_('Approvals can only be done on a method or an action, not both.'))
        Model = self.env[model]
        Model.check_access_rights('read')
        if res_id:
            record = Model.browse(res_id).exists()
            # we check that the user has read access on the underlying record before returning anything
            record.check_access_rule('read')
        domain = self._get_rule_domain(model, method, action_id)
        rules_data = self.sudo().search_read(
            domain=domain,
            fields=['group_id', 'message', 'exclusive_user', 'domain', 'can_validate', 'responsible_id', 'users_to_notify', 'notification_order'],
            order='notification_order asc, exclusive_user desc, id asc')
        applicable_rule_ids = list()
        for rule in rules_data:
            # in JS, an empty array will be truthy and I don't want to start using JSON parsing
            # instead, empty domains are replace by False here
            # done for stupid UI reasons that would take much more code to be fixed client-side
            rule_domain = rule.get('domain') and literal_eval(rule['domain'])
            rule['domain'] = rule_domain or False
            if res_id:
                if not rule_domain or record.filtered_domain(rule_domain):
                    # the record matches the domain of the rule
                    # or the rule has no domain set on it
                    applicable_rule_ids.append(rule['id'])
            else:
                applicable_rule_ids = list(map(lambda r: r['id'], rules_data))
        rules_data = list(filter(lambda r: r['id'] in applicable_rule_ids, rules_data))
        # done in sudo as users can only see their own entries through ir.rules
        entries_data = self.env['studio.approval.entry'].sudo().search_read(
            domain=[('model', '=', model), ('res_id', '=', res_id), ('rule_id', 'in', applicable_rule_ids)],
            fields=['approved', 'user_id', 'write_date', 'rule_id', 'model', 'res_id'])
        return {'rules': rules_data, 'entries': entries_data}

    @api.model
    def check_approval(self, model, res_id, method, action_id):
        """Check if the current user can proceed with an action.

        Check existing rules for the requested action and provided record; during this
        check, any rule which the user can approve will be approved automatically.

        Returns a dict indicating whether the action can proceed (`approved` key)
        (when *all* applicable rules have an entry that mark approval), as well as the
        rules and entries that are part of the approval flow for the specified action.

        :param str model: technical name of the model on which the action takes place
        :param int res_id: database ID of the record for which the action must be approved
        :param str method: method of the action that the user wants to run
        :param int action_id: database ID of the ir.actions.action that the user wants to run
        :return: a dict describing the result of the approval flow
        :rtype dict:
        :raise: UserError if action_id and method are both truthy (rules can only apply to a method
                or an action, not both)
        :raise: AccessError if the user does not have write access to the underlying record
        """
        self = self._clean_context()
        if method and action_id:
            raise UserError(_('Approvals can only be done on a method or an action, not both.'))
        record = self.env[model].browse(res_id)
        # we check that the user has write access on the underlying record before doing anything
        # if another type of access is necessary to perform the action, it will be checked
        # there anyway
        record.check_access_rights('write')
        record.check_access_rule('write')
        ruleSudo = self.sudo()
        domain = self._get_rule_domain(model, method, action_id)
        # order by 'exclusive_user' so that restrictive rules are approved first
        rules_data = ruleSudo.search_read(
            domain=domain,
            fields=['group_id', 'message', 'exclusive_user', 'domain', 'can_validate'],
            order='notification_order asc, exclusive_user desc, id asc'
        )
        applicable_rule_ids = list()
        for rule in rules_data:
            rule_domain = rule.get('domain') and literal_eval(rule['domain'])
            if not rule_domain or record.filtered_domain(rule_domain):
                # the record matches the domain of the rule
                # or the rule has no domain set on it
                applicable_rule_ids.append(rule['id'])
        rules_data = list(filter(lambda r: r['id'] in applicable_rule_ids, rules_data))
        if not rules_data:
            # no rule matching our operation: return early, the user can proceed
            return {'approved': True, 'rules': [], 'entries': []}
        # need sudo, we need to check entries from other people and through record rules
        # users can only see their own entries by default
        entries_data = self.env['studio.approval.entry'].sudo().search_read(
            domain=[('model', '=', model), ('res_id', '=', res_id), ('rule_id', 'in', applicable_rule_ids)],
            fields=['approved', 'rule_id', 'user_id'])
        entries_by_rule = dict.fromkeys(applicable_rule_ids, False)
        for rule_id in entries_by_rule:
            candidate_entry = list(filter(lambda e: e['rule_id'][0] == rule_id, entries_data))
            candidate_entry = candidate_entry and candidate_entry[0]
            if not candidate_entry:
                # there is a rule that has no entry yet, try to approve it
                try:
                    new_entry = self.browse(rule_id)._set_approval(res_id, True)
                    entries_data.append({
                        'id': new_entry.id,
                        'approved': True,
                        'rule_id': [rule_id, False],
                        'user_id': (self.env.user.id, self.env.user.display_name),
                    })
                    entries_by_rule[rule_id] = True
                except UserError:
                    # either the user doesn't have the required group, or they already
                    # validated another rule for a 'exclusive_user' approval
                    # if the rule has a responsible, create a request for them
                    self.browse(rule_id)._create_request(res_id)
                    pass
            else:
                entries_by_rule[rule_id] = candidate_entry['approved']
        return {
            'approved': all(entries_by_rule.values()),
            'rules': rules_data,
            'entries': entries_data,
        }

    def _create_request(self, res_id):
        self.ensure_one()
        ruleSudo = self.sudo()
        if not (self.responsible_id or ruleSudo.users_to_notify) or not self.model_id.sudo().is_mail_activity:
            return False
        request = self.env['studio.approval.request'].sudo().search([('rule_id', '=', self.id), ('res_id', '=', res_id)])
        if request:
            # already requested, let's not create a shitload of activities for the same user
            return False
        if self.notification_order != '1':
            # search and read entries as sudo. Otherwise we won't see entries create/approved by other users
            entry_sudo = self.env["studio.approval.entry"].sudo()
            record = self.env[ruleSudo.model_name].browse(res_id)
            # avoid asking for an approval if all request from a lower level have not yet been validated
            for approval_rule in ruleSudo.search([
                ('notification_order', '<', self.notification_order),
                ('active', '=', True),
                ("model_name", "=", ruleSudo.model_name),
                ('method', '=', ruleSudo.method),
                ('action_id', '=', ruleSudo.action_id.id)
            ]):
                rule_domain = approval_rule.domain and literal_eval(approval_rule.domain)
                if rule_domain and not record.filtered_domain(rule_domain):
                    continue
                existing_entry = entry_sudo.search([
                    ('model', '=', ruleSudo.model_name),
                    ('method', '=', ruleSudo.method),
                    ('action_id', '=', ruleSudo.action_id.id),
                    ('res_id', '=', res_id),
                    ('rule_id', '=', approval_rule.id)
                ])
                if not existing_entry or not existing_entry.approved:
                    # if rules from lower levels are not yet approved, don't create a request
                    return False

        record = self.env[self.model_name].browse(res_id)
        if self.responsible_id:
            activity_type_id = self._get_or_create_activity_type()
            activity = record.activity_schedule(activity_type_id=activity_type_id, user_id=self.responsible_id.id)
            request = self.env['studio.approval.request'].sudo().create({
                'rule_id': self.id,
                'mail_activity_id': activity.id,
                'res_id': res_id,
            })
        partner_ids = ruleSudo.users_to_notify.partner_id
        request.notify_to_users(record, ruleSudo.name, partner_ids)
        return True

    @api.model
    def _get_or_create_activity_type(self):
        approval_activity = self.env.ref('web_studio.mail_activity_data_approve', raise_if_not_found=False)
        if not approval_activity:
            # built-in activity type has been deleted, try to fallback
            approval_activity = self.env['mail.activity.type'].search([('category', '=', 'grant_approval'), ('res_model', '=', False)], limit=1)
            if not approval_activity:
                # not 'approval' activity type at all, create it on the fly
                approval_activity = self.env['mail.activity.type'].sudo().create({
                    'name': _('Grant Approval'),
                    'icon': 'fa-check',
                    'category': 'grant_approval',
                    'sequence': 999,
                })
        return approval_activity.id

    def _unlink_request(self, res_id):
        self.ensure_one()
        request = self.env['studio.approval.request'].search([('rule_id', '=', self.id), ('res_id', '=', res_id)])
        request.mail_activity_id.unlink()
        return True

class StudioApprovalEntry(models.Model):
    _name = 'studio.approval.entry'
    _description = 'Studio Approval Entry'
    # entries don't have the studio mixin since they depend on the data of the
    # db - they cannot be included into the Studio Customizations module

    @api.model
    def _default_user_id(self):
        return self.env.user

    name = fields.Char(compute='_compute_name', store=True)
    user_id = fields.Many2one('res.users', string='Approved/rejected by', ondelete='restrict',
                              required=True, default=lambda s: s._default_user_id(), index=True)
    # cascade deletion from the rule should only happen when the model itself is deleted
    rule_id = fields.Many2one('studio.approval.rule', string='Approval Rule', ondelete='cascade',
                              required=True, index=True)
    # store these for performance reasons, reading should be fast while writing can be slower
    model = fields.Char(string='Model Name', related="rule_id.model_name", store=True)
    method = fields.Char(string='Method', related="rule_id.method", store=True)
    action_id = fields.Many2one('ir.actions.actions', related="rule_id.action_id", store=True)
    res_id = fields.Many2oneReference(string='Record ID', model_field='model', required=True)
    reference = fields.Char(string='Reference', compute='_compute_reference')
    approved = fields.Boolean(string='Approved')
    group_id = fields.Many2one('res.groups', string='Group', related="rule_id.group_id")

    _sql_constraints = [('uniq_combination', 'unique(rule_id,model,res_id)', 'A rule can only be approved/rejected once per record.')]

    def init(self):
        self._cr.execute("""SELECT indexname FROM pg_indexes WHERE indexname = 'studio_approval_entry_model_res_id_idx'""")
        if not self._cr.fetchone():
            self._cr.execute("""CREATE INDEX studio_approval_entry_model_res_id_idx ON studio_approval_entry (model, res_id)""")

    @api.depends('user_id', 'model', 'res_id')
    def _compute_name(self):
        for entry in self:
            if not entry.id:
                entry.name = _('New Approval Entry')
            entry.name = '%s - %s(%s)' % (entry.user_id.name, entry.model, entry.res_id)

    @api.depends('model', 'res_id')
    def _compute_reference(self):
        for entry in self:
            entry.reference = "%s,%s" % (entry.model, entry.res_id)

    @api.model_create_multi
    def create(self, vals_list):
        entries = super().create(vals_list)
        entries._notify_approval()
        return entries

    def write(self, vals):
        res = super().write(vals)
        self._notify_approval()
        return res

    def _notify_approval(self):
        """Post a generic note on the record if it inherits mail.thread."""
        for entry in self:
            if not entry.rule_id.model_id.is_mail_thread:
                continue
            record = self.env[entry.model].browse(entry.res_id)
            record.message_post_with_source(
                'web_studio.notify_approval',
                render_values={
                    'user_name': entry.user_id.display_name,
                    'group_name': entry.group_id.display_name,
                    'approved': entry.approved,
                    },
                subtype_xmlid='mail.mt_note',
            )


class StudioApprovalRequest(models.Model):
    _name = 'studio.approval.request'
    _description = 'Studio Approval Request'

    mail_activity_id = fields.Many2one('mail.activity', string='Linked Activity', ondelete='cascade',
                                        required=True)
    rule_id = fields.Many2one('studio.approval.rule', string='Approval Rule', ondelete='cascade',
                              required=True, index=True)
    res_id = fields.Many2oneReference(string='Record ID', model_field='model', required=True)

    def notify_to_users(self, record, rule_name, partner_ids):
        """Post a request for approval note on the record."""
        if record.message_post_with_source:
            user = self.env.user
            record.message_post_with_source(
                'web_studio.request_approval',
                author_id=user.partner_id.id,
                partner_ids=partner_ids.ids,
                render_values={
                    'message': _('An approval for \'%(rule_name)s\' has been requested on %(record_name)s', rule_name=rule_name, record_name=record.name),
                    'partner_ids': partner_ids,
                    },
                subtype_xmlid='mail.mt_note',
            )
