# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast

from odoo import api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class MailMessageSubtype(models.Model):
    """ Class holding subtype definition for messages. Subtypes allow to tune
        the follower subscription, allowing only some subtypes to be pushed
        on the Wall. """
    _name = 'mail.message.subtype'
    _description = 'Message Subtype'
    _order = 'sequence, id'

    name = fields.Char(
        'Message Type', required=True, translate=True,
        help='Message subtype gives a more precise type on the message, '
             'especially for system notifications. For example, it can be '
             'a notification related to a new record (New), or to a stage '
             'change in a process (Stage change). Message subtypes allow to '
             'precisely tune the notifications the user want to receive on its wall.')
    description = fields.Text(
        'Description', translate=True, prefetch=True,
        help='Description that will be added in the message posted for this '
             'subtype. If void, the name will be added instead.')
    internal = fields.Boolean(
        'Internal Only',
        help='Messages with internal subtypes will be visible only by employees, aka members of base_user group')
    parent_id = fields.Many2one(
        'mail.message.subtype', string='Parent', ondelete='set null',
        help='Parent subtype, used for automatic subscription. This field is not '
             'correctly named. For example on a project, the parent_id of project '
             'subtypes refers to task-related subtypes.')
    relation_field = fields.Char(
        'Relation field',
        help='Field used to link the related model to the subtype model when '
             'using automatic subscription on a related document. The field '
             'is used to compute getattr(related_document.relation_field).')
    res_model = fields.Char('Model', help="Model the subtype applies to. If False, this subtype applies to all models.")
    default = fields.Boolean('Default', default=True, help="Activated by default when subscribing.")
    sequence = fields.Integer('Sequence', default=1, help="Used to order subtypes.")
    hidden = fields.Boolean('Hidden', help="Hide the subtype in the follower options")
    track_recipients = fields.Boolean('Track Recipients',
                                      help="Whether to display all the recipients or only the important ones.")
    field_tracked = fields.Char(help="Get notified when this field is updated")
    value_update = fields.Char(
        help="The notification will be sent only if the tracked field changes "
        "to the selected value. If no value is selected, "
        "it will be sent for all updates."
    )
    domain = fields.Char(
        help="The notification will be sent only for records that match the selected domain."
    )
    user_ids = fields.Many2many("res.users", help="Users that have access to this subtype.")
    is_custom = fields.Boolean("Is Custom", compute="_compute_is_custom")

    @api.constrains("res_model")
    def _check_res_model(self):
        for subtype in self:
            if not subtype.res_model:
                continue
            if subtype.res_model not in self.env:
                raise ValidationError(
                    self.env._("The model '%s' does not exist.", subtype.res_model)
                )

    @api.constrains("field_tracked", "res_model")
    def _check_field_tracked(self):
        for subtype in self:
            if not subtype.field_tracked:
                continue
            model = self.env[subtype.res_model]
            if subtype.field_tracked not in model._fields:
                raise ValidationError(
                    self.env._(
                        "The field '%(field_tracked)s' does not exist on model '%(res_model)s'.",
                        field_tracked=subtype.field_tracked,
                        res_model=subtype.res_model,
                    )
                )

    @api.constrains("domain", "res_model")
    def _check_domain(self):
        for subtype in self:
            if not subtype.domain:
                continue
            model = self.env[subtype.res_model]
            try:
                query = model.sudo()._search(subtype._get_domain())
                sql = tools.SQL("EXPLAIN %s", query.select())
                with tools.mute_logger("odoo.sql_db"):
                    self.env.cr.execute(sql)
            except Exception:  # noqa: BLE001
                raise ValidationError(
                    self.env._(
                        "The domain '%(domain)s' is not valid on model '%(res_model)s'.",
                        domain=subtype.domain,
                        res_model=subtype.res_model,
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        self.env.registry.clear_cache()  # _get_auto_subscription_subtypes
        return super(MailMessageSubtype, self).create(vals_list)

    def write(self, vals):
        self.env.registry.clear_cache()  # _get_auto_subscription_subtypes
        return super(MailMessageSubtype, self).write(vals)

    def unlink(self):
        self.env.registry.clear_cache()  # _get_auto_subscription_subtypes
        return super(MailMessageSubtype, self).unlink()

    @api.depends("field_tracked")
    def _compute_is_custom(self):
        for subtype in self:
            subtype.is_custom = bool(subtype.field_tracked)

    @tools.ormcache('model_name')
    def _get_auto_subscription_subtypes(self, model_name):
        """ Return data related to auto subscription based on subtype matching.
        Here model_name indicates child model (like a task) on which we want to
        make subtype matching based on its parents (like a project).

        Example with tasks and project :

         * generic: discussion, res_model = False
         * task: new, res_model = project.task
         * project: task_new, parent_id = new, res_model = project.project, field = project_id

        Returned data

          * child_ids: all subtypes that are generic or related to task (res_model = False or model_name)
          * def_ids: default subtypes ids (either generic or task specific)
          * all_int_ids: all internal-only subtypes ids (generic or task or project)
          * parent: dict(parent subtype id, child subtype id), i.e. {task_new.id: new.id}
          * relation: dict(parent_model, relation_fields), i.e. {'project.project': ['project_id']}
        """
        child_ids, def_ids = list(), list()
        all_int_ids = list()
        parent, relation = dict(), dict()
        subtypes = self.sudo().search([
            '|', '|', ('res_model', '=', False),
            ('res_model', '=', model_name),
            ('parent_id.res_model', '=', model_name)
        ])
        for subtype in subtypes:
            if not subtype.res_model or subtype.res_model == model_name:
                child_ids += subtype.ids
                if subtype.default:
                    def_ids += subtype.ids
            if subtype.relation_field:
                parent[subtype.id] = subtype.parent_id.id
                relation.setdefault(subtype.res_model, set()).add(subtype.relation_field)
            # required for backward compatibility
            if subtype.internal:
                all_int_ids += subtype.ids
        return child_ids, def_ids, all_int_ids, parent, relation

    @api.model
    def default_subtypes(self, model_name):
        """ Retrieve the default subtypes (all, internal, external) for the given model. """
        subtype_ids, internal_ids, external_ids = self._default_subtypes(model_name)
        return self.browse(subtype_ids), self.browse(internal_ids), self.browse(external_ids)

    @tools.ormcache('self.env.uid', 'self.env.su', 'model_name')
    def _default_subtypes(self, model_name):
        domain = [('default', '=', True),
                  '|', ('res_model', '=', model_name), ('res_model', '=', False)]
        subtypes = self.search(domain)
        internal = subtypes.filtered('internal')
        return subtypes.ids, internal.ids, (subtypes - internal).ids

    def _get_domain(self):
        self.ensure_one()
        if not self.domain:
            return Domain()
        return Domain(ast.literal_eval(self.domain))

    @api.model
    def _get_matching_fields_tracked_subtypes(self, thread, fields):
        """Return the subtypes matching the given thread and fields.

        :param thread: mail.thread record
        :param fields: list of fields that have been updated on the thread
        :return: mail.message.subtype recordset
        """
        # sudo: search for other users subtypes to notify them if needed
        return (
            self.env["mail.message.subtype"]
            .sudo()
            .search_fetch(
                Domain("res_model", "=", thread._name) & Domain("field_tracked", "in", fields),
                ["id", "field_tracked", "value_update", "domain"],
            )
        )

    def _filter_matching_subtypes(self, thread, fields):
        thread.ensure_one()

        def is_matching(subtype):
            if not subtype.is_custom:
                return False
            return subtype._is_matching_custom_subtypes(thread, fields)

        return self.filtered(is_matching)

    def _is_matching_custom_subtypes(self, thread, fields):
        thread.ensure_one()
        self.ensure_one()
        if self.field_tracked not in fields:
            return False
        if not self.value_update:
            return True
        tracked_field_name = self.field_tracked
        tracked_field = thread._fields.get(self.field_tracked)
        match tracked_field.type:
            case "many2one" | "integer":
                value_update = int(self.value_update)
            case "float" | "monetary":
                value_update = float(self.value_update)
            case "boolean":
                value_update = self.value_update.lower() == "true"
            case _:
                value_update = self.value_update

        domain = Domain(tracked_field_name, "=", value_update)
        return len(thread.filtered_domain(domain)) > 0
