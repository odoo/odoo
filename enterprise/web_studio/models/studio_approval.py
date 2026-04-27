# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
import logging

from odoo import api, models, fields, _, Command
from odoo.osv import expression
from odoo.exceptions import ValidationError, UserError
from collections import defaultdict


_logger = logging.getLogger(__name__)


class StudioApprovers(models.Model):
    _name = "studio.approval.rule.approver"
    _description = "Approval Rule Approvers Enriched"
    _order = "id desc"
    _log_access = True  # explicit: we need create_uid and create_date

    user_id = fields.Many2one("res.users", required=True, ondelete="cascade")
    rule_id = fields.Many2one("studio.approval.rule", required=True, ondelete="cascade")
    date_to = fields.Date()
    is_delegation = fields.Boolean(default=True)

    @api.depends("create_uid", "user_id", "date_to")
    def _compute_display_name(self):
        for rec in self:
            name = []
            if rec.create_uid.name:
                name.extend([rec.create_uid.name, _("delegates to %s.", rec.user_id.name)])
            else:
                name.append(_("to %s.", rec.user_id.name))

            if rec.date_to:
                val = rec._fields["date_to"].convert_to_display_name(rec.date_to, rec)
                name.append(_("Until %s", val))
            rec.display_name = " ".join(name)

    def _is_valid(self):
        return not self.date_to or self.date_to >= fields.Date.context_today(self)

    def _filtered_valid(self):
        return self.filtered(lambda rec: rec._is_valid())

class StudioApprovalRule(models.Model):
    _name = "studio.approval.rule"
    _description = "Studio Approval Rule"
    _inherit = ["studio.mixin", 'mail.thread']

    @api.model
    def _parse_action_from_button(self, str_action):
        if not str_action:
            return False
        try:
            return int(str_action)
        except ValueError:
            action = self.env.ref(str_action, raise_if_not_found=False)
            return action and action.id

    def _group_expand_notification_order(self, options, domain):
        return sorted(set(options).union({'1', '2', '3', '4'}))

    active = fields.Boolean(default=True)
    model_id = fields.Many2one("ir.model", string="Model", ondelete="cascade", required=True)
    method = fields.Char(string="Method")
    action_id = fields.Many2one("ir.actions.actions", string="Action", ondelete="cascade")
    action_xmlid = fields.Char(related="action_id.xml_id", search="_search_action_xmlid")
    name = fields.Char()
    message = fields.Char(translate=True, string="Description", help="The step description will be displayed on the button on which an approval is requested.")
    approver_ids = fields.Many2many(
        comodel_name='res.users',
        compute='_compute_approver_ids',
        inverse="_inverse_approver_ids",
        string='Approvers',
        help="These users are able to approve or reject the step and will be assigned to an activity when their approval is requested.",
        domain="[('id', 'not in', [1]), ('share', '=', False)]",
        tracking=True
    )
    approver_log_ids = fields.One2many("studio.approval.rule.approver", inverse_name="rule_id", tracking=True)
    approval_group_id = fields.Many2one(comodel_name='res.groups', string='Approval Group', help="The users in this group are able to approve or reject the step.", tracking=True)
    users_to_notify = fields.Many2many(
        comodel_name='res.users',
        relation='approval_rule_users_to_notify_rel',
        string='Users to Notify',
        domain="[('id', 'not in', [1]), ('share', '=', False)]",
        help="These users will receive a notification via internal note when the step is approved or rejected"
    )
    notification_order = fields.Selection(
        selection=[
            ('1', 'Step 1'),
            ('2', 'Step 2'),
            ('3', 'Step 3'),
            ('4', 'Step 4'),
            ('5', 'Step 5'),
            ('6', 'Step 6'),
            ('7', 'Step 7'),
            ('8', 'Step 8'),
            ('9', 'Step 9')
        ],
        string='Step',
        default='1',
        group_expand=_group_expand_notification_order,
        help="Defines the sequential order in which the approvals are requested."
    )
    exclusive_user = fields.Boolean(string="Exclusive Approval",
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
    kanban_color = fields.Integer(compute="_compute_kanban_color")
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

    @api.depends("notification_order")
    def _compute_display_name(self):
        string_notification_order = dict(self._fields['notification_order']._description_selection(self.env))
        for rec in self:
            rec.display_name = string_notification_order[rec.notification_order]

    @api.depends("approver_log_ids")
    def _compute_approver_ids(self):
        for rec in self.sudo():
            rec.approver_ids = rec.approver_log_ids._filtered_valid().user_id

    def _inverse_approver_ids(self):
        for rec in self:
            track_message = _("%(user_name)s has set approval rights from %(previous_approvers)s to %(next_approvers)s",
                user_name=self.env.user.name,
                previous_approvers=", ".join(self.approver_log_ids.filtered(lambda log: not log.is_delegation).user_id.mapped("name")) or _("no one"),
                next_approvers=", ".join(rec.approver_ids.mapped("name")) or _("no one")
                )
            rec._track_set_log_message(track_message)
            commands = rec._get_approver_log_changes({"approver_ids": rec.approver_ids})
            rec.approver_log_ids = commands

    def _get_approver_log_changes(self, data):
        approvers = data.get("approver_ids")
        if approvers is not None and not data.get("approver_log_ids"):
            approver_ids = self._fields["approver_ids"].convert_to_cache(approvers, self)
            commands = [Command.clear()]
            commands.extend([Command.create({"user_id": _id, "is_delegation": False}) for _id in approver_ids])
            return commands
        return None

    def _delegate_to(self, user_ids, date_to):
        self.ensure_one()
        commands = []
        revoked_users = []
        for log in self.approver_log_ids:
            if not log._is_valid():
                commands.append(Command.delete(log.id))
            elif log.create_uid.id == self.env.uid and log.is_delegation:
                commands.append(Command.delete(log.id))
                revoked_users.append(log.user_id.id)

        for approver_id in user_ids:
            commands.append(Command.create({
                "user_id": approver_id.id,
                "date_to": date_to,
                "is_delegation": True
            }))

        if user_ids:
            message = _("%(user_name)s delegated approval rights to %(delegate_to)s",
                        user_name=self.env.user.name,
                        delegate_to=", ".join(user_ids.mapped("name")))
            if date_to:
                approver_model = self.env["studio.approval.rule.approver"]
                date_field = approver_model._fields["date_to"]
                val = date_field.convert_to_display_name(date_to, approver_model)
                message += _(" until %s", val)
            self._track_set_log_message(message)
        elif revoked_users:
            revoked_users = self.env["res.users"].browse(revoked_users)
            message = _("%(user_name)s revoked their delegation to %(revoked_users)s",
                        user_name=self.env.user.name,
                        revoked_users=", ".join(revoked_users.mapped("name")))
            self._track_set_log_message(message)
        self.write({"approver_log_ids": commands})

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
                        _("There is no method %(method)s on the model %(model_name)s (%(model_id)s)",
                        method=rule.method, model_name=rule.model_id.name, model_id=rule.model_id.model)
                    )
                if rule.method in ["create", "write", "unlink"]:
                    # base_automation and studio_approval executes delattr command in their
                    # unregister_hook before re-patching in their register_hook.
                    # However base_automation will not re-patch approvals and vice versa.

                    raise ValidationError(_("For compatibility purpose with base_automation,"
                                            "approvals on 'create', 'write' and 'unlink' methods "
                                            "are forbidden."))

    def _search_action_xmlid(self, operator, value):
        supported_ops = ("=", "in", "!=", "not in")
        if operator not in supported_ops:
            raise UserError(_("Unsupported operator '%s' to search action_xmlid", operator))

        is_list = isinstance(value, list)
        value = value if is_list else [value]
        action_ids = [self._parse_action_from_button(v) for v in value]
        return [("action_id", operator, action_ids if is_list else action_ids[0])]

    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        default_model_name = self._context.get("default_model_name")
        if default_model_name and "model_id" in fields_list and not vals.get("model_id"):
            vals["model_id"] = self.env["ir.model"]._get(default_model_name)
        default_action_xmlid = self._context.get("default_action_xmlid")
        if default_action_xmlid and "action_id" in fields_list and not vals.get("action_id"):
            action_id = self._parse_action_from_button(default_action_xmlid)
            if action_id:
                vals["action_id"] = self._parse_action_from_button(default_action_xmlid)
        return vals

    def write(self, vals):
        if "approver_log_ids" in vals:
            vals.pop("approver_ids", None)
        write_readonly_fields = bool(set(vals.keys()) & {'model_id', 'method', 'action_id'})
        if write_readonly_fields and any(rule.entry_ids for rule in self):
            raise UserError(_(
                "Rules with existing entries cannot be modified since it would break existing "
                "approval entries. You should archive the rule and create a new one instead."))
        res = super().write(vals)
        self._update_registry()
        return res

    def _base_automation_data_for_model(self, model_id):
        # Careful here, this method implements things specific to actual models
        # So, be aware that if you put specific code for a model that is not present
        # in the registry, chances are there will be a crash
        model_name = model_id.model
        if model_name == "sale.order":
            state_field = self.env["ir.model.fields"]._get("sale.order", "state")
            return {
                'trigger': 'on_state_set',
                'trg_selection_field_id': state_field.selection_ids.filtered(lambda s: s.value == "draft").id,
                'filter_pre_domain': "[('state', '!=', 'draft')]",
            }
        if model_name == "account.move":
            state_field = self.env["ir.model.fields"]._get("account.move", "state")
            return {
                'trigger': 'on_state_set',
                'trg_selection_field_id': state_field.selection_ids.filtered(lambda s: s.value == "draft").id,
                'filter_pre_domain': "[('state', '!=', 'draft')]",
            }
        if model_name == "purchase.order":
            state_field = self.env["ir.model.fields"]._get("purchase.order", "state")
            return {
                'trigger': 'on_state_set',
                'trg_selection_field_id': state_field.selection_ids.filtered(lambda s: s.value == "draft").id,
                'filter_pre_domain': "[('state', '!=', 'draft')]",
            }
        return None

    def _make_automated_actions(self):
        def process_xml_id_params(model_name, module_prefix=None):
            if module_prefix is None:
                module_prefix = "web_studio"
            return model_name.replace(".", "_"), module_prefix + "." if module_prefix else ""

        def get_base_automation_xml_id(model_name, module_prefix=None):
            model_name, module_prefix = process_xml_id_params(model_name, module_prefix)
            return f"{module_prefix}remove_approval_entries__{model_name}__automation"

        def get_base_action_server_xml_id(model_name, module_prefix=None):
            model_name, module_prefix = process_xml_id_params(model_name, module_prefix)
            return f"{module_prefix}remove_approval_entries__{model_name}__action_server"

        self_sudo = self.sudo()
        new_automations = []
        for model_id in self_sudo.mapped("model_id"):
            model = model_id.model
            base_auto_data = self_sudo._base_automation_data_for_model(model_id)
            if base_auto_data is None:
                continue

            specific_ref = get_base_automation_xml_id(model)
            if self_sudo.env.ref(specific_ref, raise_if_not_found=False):
                continue
            automation = {
                "name": f"Reset approval entries for ({model_id.name})",
                "model_id": model_id.id,
                **base_auto_data,
            }
            new_automations.append(automation)

        automations = self_sudo.env["base.automation"].create(new_automations)

        actions_server_data = []
        xml_ids_data = []
        for base_auto in automations:
            model_id = base_auto.model_id
            model = model_id.model
            xml_ids_data.append({
                "name": get_base_automation_xml_id(model, module_prefix=""),
                "model": "base.automation",
                "res_id": base_auto.id,
                "module": "web_studio",
                "noupdate": True,
            })
            server_action = self_sudo.env.ref(get_base_action_server_xml_id(model), raise_if_not_found=False)
            if server_action:
                server_action.write({
                    "base_automation_id": base_auto.id,
                    "model_id": model_id.id
                })
            else:
                actions_server_data.append({
                    "name": f"Reset approval entries for ({model_id.name})",
                    "base_automation_id": base_auto.id,
                    'state': 'code',
                    'code': "records.env['studio.approval.entry']._delete_entries(records)",
                    "model_id": model_id.id,
                })

        for server_action in self_sudo.env["ir.actions.server"].create(actions_server_data):
            model_data_name = get_base_action_server_xml_id(server_action.model_id.model, module_prefix="")
            xml_ids_data.extend([{
                    "name": model_data_name,
                    "model": "ir.actions.server",
                    "res_id": server_action.id,
                    "module": "web_studio",
                    "noupdate": True,
                }, {
                    "name": model_data_name,
                    "model": "ir.actions.server",
                    "res_id": server_action.id,
                    "module": "__cloc_exclude__",
                }
            ])

        self_sudo.env["ir.model.data"].create(xml_ids_data)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "approver_log_ids" in vals:
                vals.pop("approver_ids", None)
        rules = super().create(vals_list)
        rules._make_automated_actions()
        self._update_registry()
        return rules

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
                        missing_approvals = self.env['studio.approval.rule'].get_missing_approvals(rules[0], entries[0])
                        message += _('Some approvals are missing') if len(missing_approvals) > 1 else _('An approval is missing')

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

    @api.ondelete(at_uninstall=False)
    def _unlink_except_existing_entries(self):
        if any(rule.entry_ids for rule in self):
            raise UserError(_(
                "Rules with existing entries cannot be deleted since it would delete existing "
                "approval entries. You should archive the rule instead."))

    @api.depends('approval_group_id', 'approver_ids')
    @api.depends_context("uid")
    def _compute_can_validate(self):
        user = self.env.user
        for rule in self:
            rule.can_validate = user in rule.approver_ids or user in rule.approval_group_id.users

    @api.depends('can_validate')
    def _compute_kanban_color(self):
        for rule in self:
            rule.kanban_color = 7 if rule.can_validate else 0

    @api.depends("domain")
    def _compute_conditional(self):
        for rule in self:
            rule.conditional = bool(rule.domain)

    @api.depends('entry_ids')
    def _compute_entries_count(self):
        for rule in self:
            rule.entries_count = len(rule.entry_ids)

    @api.model
    def create_rule(self, model, method, action_id, notification_order=None):
        model = self.env['ir.model']._get(model)
        values = {
            'model_id': model.id,
            'method': method,
            'action_id': self._parse_action_from_button(action_id),
        }
        if notification_order is not None:
            values["notification_order"] = notification_order
        return self.create(values)

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
        record.check_access('write')
        ruleSudo = self.sudo()

        existing_entry = self.env['studio.approval.entry'].sudo().search([
                ('model', '=', ruleSudo.model_name),
                ('method', '=', ruleSudo.method), ('action_id', '=', ruleSudo.action_id.id),
                ('res_id', '=', res_id), ('rule_id', '=', self.id)])
        if existing_entry and existing_entry.user_id != self.env.user:
            rules_above = self.env["studio.approval.rule"].sudo().search_read([
                ('model_name', '=', ruleSudo.model_name),
                ('method', '=', ruleSudo.method), ('action_id', '=', ruleSudo.action_id.id),
                ('notification_order', ">", ruleSudo.notification_order)
            ], ["domain", "can_validate"], order="notification_order DESC")

            can_revoke = False
            for rule in rules_above:
                domain = literal_eval(rule["domain"] or "[]")
                if not record.filtered_domain(domain):
                    continue
                if rule["can_validate"]:
                    can_revoke = True
                    break

            if not can_revoke:
                # this should normally not happen because of ir.rules, but let's be careful
                # when dealing with security
                raise UserError(_("You cannot cancel an approval you didn't set yourself or you don't belong to an higher level rule's approvers."))
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
        if not all_rule_ids:
            return None
        self.env.cr.execute('SELECT id FROM studio_approval_rule WHERE id IN %s FOR UPDATE NOWAIT', (all_rule_ids,))
        # NOTE: despite the 'NOWAIT' modifier, the query will actually be retried by
        # Odoo itself (not PG); the NOWAIT ensures that no deadlock will happen
        # check if the user has write access to the record
        record = self.env[self.sudo().model_name].browse(res_id)
        record.check_access('write')
        # check if the user has the necessary group
        if not ruleSudo.can_validate:
            raise UserError(
                _('You can not approve this rule.')
            )

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

        if approved and ruleSudo.notification_order != '9':
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

            should_notify_higher = not same_level_rules
            if same_level_rules:
                approved_entries = ruleSudo.env["studio.approval.entry"].search_read([
                    ("rule_id", "in", same_level_rules), ("res_id", "=", record.id), ("approved", "=", True)
                ], ["rule_id"])
                if approved_entries:
                    entry_rule_ids = {entry["rule_id"][0] for entry in approved_entries}
                    should_notify_higher = all(same_level_id in entry_rule_ids for same_level_id in same_level_rules)
                else:
                    should_notify_higher = False
            if should_notify_higher:
                for rule in ruleSudo.browse(higher_level_rules):
                    rule._create_request(res_id)
        return result

    def _get_rule_domain(self, model, method, action_id):
        # just in case someone didn't cast it properly client side, would be
        # a shame to be able to skip this 'security' because of a missing parseInt 😜
        action_id = self._parse_action_from_button(action_id)
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
    def _get_approval_spec(self, model, spec):
        """
        Gets the approval specification for a given model according
        to specifications. Those are a directory of what approvals and
        entries we should fetch, based on method, action_id and res_id

        Arguments:
            :param model: string
                the name of the model of which we want the approvals
            :param spec: dict
                An object containing the specifications of the approvals we want.
                {
                    (method, action_id): set<int>,
                    ...
                }
                Note that method and action_id are mutually exclusive. The tuple allows to both be used as
                a dict key and to know where to find the relevant information.

        Returns:
            :returns  tuple: (model, map_rules, results)
                model: the model's name
                map_rules: dict: {
                    int: { **record.read() },
                    ...
                }
                results: dict: {
                    (res_id, method, action_id): { "rules": int[], "entries": dict[] },
                    ...
                }
        """
        records = self.env[model]
        records.check_access('read')

        def m2o_to_id(t_uple):
            return t_uple and t_uple[0]

        # Harvest all res_ids, method names, and action_ids
        # to be able to pass one batching search query
        all_res_ids = set()
        all_methods = set()
        all_action_ids = set()
        for (method, action_id), ids in spec.items():
            all_res_ids |= ids
            if method:
                all_methods.add(method)
            if action_id:
                all_action_ids.add(action_id)
        res_ids = [_id for _id in all_res_ids if _id]
        if res_ids:
            records = records.browse(res_ids).exists()
            # we check that the user has read access on the underlying record before returning anything
            records.check_access('read')

        # Search every rule matching all methods and actions: we'll map those results afterwards
        rules_domain = [('model_name', '=', model)]
        rules_domain = expression.AND([rules_domain, [
            "|", ("method", "in", list(all_methods)),
            ("action_id", "in", list(all_action_ids))
        ]])
        rules_data = self.sudo().search_read(
            domain=rules_domain,
            fields=['name', 'message', 'exclusive_user', 'can_validate', 'action_id', 'method', "approver_ids", "users_to_notify", "approval_group_id", "notification_order", "domain"],
            order='notification_order asc, exclusive_user desc, id asc')

        # Process rules by remapping to the specs
        # Harvest data to be able to search for entries afterwards
        # Start building the result: each res_id in the spec matches
        # a key (res_id, method, action_id)
        results = defaultdict(dict)
        res_ids_for_entries = set()
        rule_ids_for_entries = set()
        map_rules = {}
        for rule in rules_data:
            map_rules[rule["id"]] = rule

            res_ids_for_rule = spec[(rule["method"], m2o_to_id(rule["action_id"]))]
            records_for_rule = records.browse([_id for _id in res_ids_for_rule if _id]).with_prefetch(records.ids or None)
            # in JS, an empty array will be truthy and I don't want to start using JSON parsing
            # instead, empty domains are replace by False here
            # done for stupid UI reasons that would take much more code to be fixed client-side
            rule_domain = rule.get('domain') and literal_eval(rule['domain'])
            rule['domain'] = rule_domain or False

            record_ids_for_result = list()
            if records_for_rule:
                if not rule_domain:
                    record_ids_for_result = records_for_rule.ids
                else:
                    impacted_records = records_for_rule.filtered_domain(rule_domain)
                    record_ids_for_result = impacted_records.ids

            # Push rule here to search for entries
            # we won't fetch entries for the False res_id
            if record_ids_for_result:
                rule_ids_for_entries.add(rule["id"])

            if False in res_ids_for_rule:
                record_ids_for_result.append(False)

            for res_id in record_ids_for_result:
                if res_id:  # Don't push "False": we don't want to pass a useless search query
                    res_ids_for_entries.add(res_id)
                res_key = (res_id, rule["method"], m2o_to_id(rule["action_id"]))
                results[res_key] = results.get(res_key, {"rules": [], "entries": []})
                results[res_key]["rules"].append(rule["id"])

        if rule_ids_for_entries:
            # Search for entries according to res_ids and rule_ids: we'll re-group them after
            # done in sudo as users can only see their own entries through ir.rules
            entries_data = self.env['studio.approval.entry'].sudo().search_read(
                domain=[('model', '=', model), ('res_id', 'in', list(res_ids_for_entries)), ('rule_id', 'in', list(rule_ids_for_entries))],
                fields=['approved', 'user_id', 'write_date', 'rule_id', 'model', 'res_id'])

            # Process entries
            # fillup each returned approval_spec according to the key
            # (res_id, method, action_id) with the matching entries.
            for entry in entries_data:
                rule = map_rules[entry["rule_id"][0]]
                key = (entry["res_id"], rule["method"], m2o_to_id(rule["action_id"]))
                results[key]["entries"].append(entry)

        return model, map_rules, results

    @api.model
    def get_approval_spec(self, args_list):
        """Get the approval spec for a list of buttons and records.

        An approval spec is a dict containing information regarding approval rules
        and approval entries for the action described with the model/method/action_id
        arguments (method and action_id cannot be truthy at the same time).

        The `rules` entry of the returned dict contains a description of the approval rules
        for the current record: the group required for its approval, the message describing
        the reason for the rule to exist, whether it can be approved if other rules for the
        same record have been approved by the same user, a domain (if the rule is conditional)
        and a computed 'can_validate' field which specifies whether the current user is in the
        required group to approve the rule. This entry contains a read_group result on the
        rule model for the fields 'group_id?', 'message', 'exclusive_user', 'domain' and
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

        :param list args_list: A list of dictionaries containing the following keys:
            - model (str): Technical name of the model for the requested spec.
            - method (str): Method for the spec.
            - action_id (int): Database ID of the ir.actions.action record for the spec.
            - res_id (int): Database ID of the record for which the spec must be checked.
                Defaults to False.
        :return: a dict containing all rules that are used by by records.
                records are contained under their model's key, under the form of a list of tuples
                So doing dict(get_approval_spec[model_name]) gives all the records keyed by (res_id, method, action_id)
                {
                    "all_rules": { [id]: rule },
                    [model_name]: [((res_id, method, action_id), { rules: [], entries: [] }), ... ]
                }
        :rtype dict:
        :raise: UserError if action_id and method are both truthy (rules can only apply to a method
                or an action, not both)
        :raise: AccessError if the user does not have read access to the underlying model (and record
                if res_id is specified)
        """
        self = self._clean_context()
        # First, group all arguments to get a dictionary of the form
        # {
        #   [model_name]: {
        #      (method, action_id): set<int>, ...
        #   },
        #   ...
        # }
        grouped_model = dict()
        actions_map = dict()
        for args in args_list:
            method = args.get("method") or False
            action_id_origin = args.get("action_id") or False
            action_id = self._parse_action_from_button(action_id_origin)
            actions_map[action_id] = action_id_origin
            model = args["model"]
            model_group = grouped_model[model] = grouped_model.get(model, defaultdict(set))
            if method and action_id:
                raise UserError(_('Approvals can only be done on a method or an action, not both.'))
            res_id = args.get("res_id") or False
            if res_id:
                res_id = int(res_id)
            model_group[(method, action_id)].add(res_id)

        # Actually get approval specs for each model
        # Then, return a dict containing all_rules used by approval specs
        # and the specs themselves.
        # we return a list of tuples for each model to be compatible with
        # a JSON serialization.
        result = {"all_rules": {}}

        for model, spec in grouped_model.items():
            model, rules, results = self._get_approval_spec(model, spec)
            result["all_rules"].update(rules)
            tuple_list = []
            for (res_id, method, action_id), val in results.items():
                tuple_list.append(((res_id, method, actions_map.get(action_id, action_id)), val))
            result[model] = tuple_list

        return result

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
        record.check_access('write')
        ruleSudo = self.sudo()
        domain = self._get_rule_domain(model, method, action_id)
        # order by 'exclusive_user' so that restrictive rules are approved first
        rules_data = ruleSudo.search_read(
            domain=domain,
            fields=['message', 'name', 'domain'],
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
        if not self.model_id.sudo().is_mail_activity:
            return False

        users = ruleSudo.approver_ids
        if not users:
            return False

        requests = self.env['studio.approval.request'].sudo().search([('rule_id', '=', self.id), ('res_id', '=', res_id)])
        if requests:
            # already requested, let's not create a shitload of activities for the same users
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
        activity_type_id = self._get_or_create_activity_type()
        activity_ids = []
        for user in users:
            activity = record.activity_schedule(activity_type_id=activity_type_id, user_id=user.id)
            activity_ids.append(activity.id)

        self.env['studio.approval.request'].sudo().create([
            {
                'rule_id': self.id,
                'mail_activity_id': activity_id,
                'res_id': res_id,
            }
            for activity_id in activity_ids
        ])

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
        requests = self.env['studio.approval.request'].search([('rule_id', '=', self.id), ('res_id', '=', res_id)])
        requests.mail_activity_id.unlink()
        return True

    def open_delegate_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Delegate to"),
            "target": "new",
            "res_model": "studio.approval.rule.delegate",
            "views": [[False, "form"]],
            "context": {
                "active_test": True,
                "default_approval_rule_id": self.id,
            }
        }

    def open_kanban_rules(self, model, method=False, action=False):
        model_id = self.env["ir.model"]._get(model)
        context = {
            "default_model_id": model_id.id,
            "search_view_ref": "web_studio.studio_approval_rule_button_configuration_search_view",
            "search_default_notification_order": True,
        }
        domain = [("model_id", "=", model_id.id)]
        if method:
            context["default_method"] = method
            domain.append(("method", "=", method))
        else:
            action_id = self._parse_action_from_button(action)
            context["default_action_id"] = action_id
            domain.append(("action_id", "=", action_id))

        return {
            "name": _("Approvals %(model_name)s", model_name=model_id.name),
            "res_model": "studio.approval.rule",
            "type": "ir.actions.act_window",
            "views": [
                [False, "kanban"],
                [False, "list"],
                [False, "form"],
            ],
            "domain": domain,
            "context": context,
        }

    # Tracking Values
    def _track_filter_for_display(self, tracking_values):
        approver_log_field = self.env["ir.model.fields"]._get(self._name, "approver_log_ids")
        approver_ids_field = self.env["ir.model.fields"]._get(self._name, "approver_ids")
        return tracking_values.filtered(lambda tv: tv.field_id not in [approver_log_field, approver_ids_field])

    def _mail_track(self, tracked_fields, initial_values):
        # The one2many may have some deleted records
        # pop the whole thing to always have the custom message
        # and avoid a MissingError
        initial_values.pop("approver_log_ids", None)
        return super()._mail_track(tracked_fields, initial_values)


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

    def _delete_entries(self, records):
        model_name = records._name
        existing_entries = self.sudo().env['studio.approval.entry'].search([
            ('model', '=', model_name),
            ('res_id', 'in', records.ids)
        ])
        existing_entries.unlink()

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
            partner_ids = entry.rule_id.users_to_notify.partner_id
            rule = entry.rule_id
            target_name = ""
            if rule.name:
                target_name = rule.name
            elif rule.method:
                target_name = _("Method: %s", rule.method)
            elif rule.action_id.name:
                target_name = _("Action: %s", rule.action_id.name)

            record.message_post_with_source(
                'web_studio.notify_approval',
                author_id=entry.user_id.partner_id.id,
                partner_ids=partner_ids.ids,
                render_values={
                    'partner_ids': partner_ids,
                    'target_name': target_name,
                    'user_name': entry.user_id.display_name,
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


class StudioApprovalRuleDelegate(models.TransientModel):
    _name = "studio.approval.rule.delegate"
    _description = "Approval Rule Delegate"

    approval_rule_id = fields.Many2one("studio.approval.rule", required=True)
    approver_ids = fields.Many2many("res.users", string="Approvers",
        domain="['&', ('id', 'not in', [uid, 1]), ('share', '=', False)]")
    users_to_notify = fields.Many2many("res.users",
        relation="res_user_approval_rule_notify_rel",
        domain="[('id', 'not in', [1]), ('share', '=', False)]",
        string="Notify to")
    date_to = fields.Date(string="Until")

    def create(self, vals):
        records = super().create(vals)
        for rec in records:
            rule = rec.approval_rule_id.sudo()
            rule._delegate_to(rec.approver_ids, rec.date_to)
            rule.write({"users_to_notify": rec.users_to_notify})
        return records

    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        default_rule_id = self.env.context.get("default_approval_rule_id")
        if default_rule_id and "approver_ids" in fields_list and "users_to_notify" in fields_list:
            rule = self.env["studio.approval.rule"].browse(default_rule_id).sudo()
            vals["approver_ids"] = [Command.link(log.user_id.id) for log in rule.approver_log_ids if log.is_delegation and log.create_uid.id == self.env.uid]
            vals["users_to_notify"] = [Command.link(uid) for uid in rule.users_to_notify.ids]
        return vals
