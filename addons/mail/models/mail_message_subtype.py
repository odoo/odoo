# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class MailMessageSubtype(models.Model):
    """ Class holding subtype definition for messages. Subtypes allow to tune
        the follower subscription, allowing only some subtypes to be pushed
        on the Wall. """
    _name = 'mail.message.subtype'
    _description = 'Message subtypes'
    _order = 'sequence, id'

    name = fields.Char(
        'Message Type', required=True, translate=True,
        help='Message subtype gives a more precise type on the message, '
             'especially for system notifications. For example, it can be '
             'a notification related to a new record (New), or to a stage '
             'change in a process (Stage change). Message subtypes allow to '
             'precisely tune the notifications the user want to receive on its wall.')
    description = fields.Text(
        'Description', translate=True,
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

    @api.model
    def create(self, vals):
        self.clear_caches()
        return super(MailMessageSubtype, self).create(vals)

    @api.multi
    def write(self, vals):
        self.clear_caches()
        return super(MailMessageSubtype, self).write(vals)

    @api.multi
    def unlink(self):
        self.clear_caches()
        return super(MailMessageSubtype, self).unlink()

    @tools.ormcache('self.env.uid', 'model_name')
    def _get_auto_subscription_subtypes(self, model_name):
        """ Return data related to auto subscription based on subtype matching.
        Example with tasks and project :

         * generic: discussion, res_model = False
         * task: new, res_model = project.task
         * project: task_new, parent_id = new, res_model = project.project, field = project_id

        Returned data

          * all_ids: all subtypes that are generic or related to task and project
          * def_ids: for task, default subtypes ids
          * int_ids: for task, internal-only default subtypes ids
          * parent: dict(parent subtype id, child subtype id), i.e. {task_new.id: new.id}
          * relation: dict(parent_model, relation_fields), i.e. {'project.project': ['project_id']}
        """
        all_ids, def_ids, int_ids, parent, relation = list(), list(), list(), dict(), dict()
        subtypes = self.sudo().search([
            '|', '|', ('res_model', '=', False),
            ('res_model', '=', model_name),
            ('parent_id.res_model', '=', model_name)
        ])
        for subtype in subtypes:
            if not subtype.res_model or subtype.res_model == model_name:
                all_ids += subtype.ids
                if subtype.default:
                    def_ids += subtype.ids
            elif subtype.relation_field:
                parent[subtype.id] = subtype.parent_id.id
                relation.setdefault(subtype.res_model, set()).add(subtype.relation_field)
            if subtype.internal:
                int_ids += subtype.ids
        return all_ids, def_ids, int_ids, parent, relation

    @api.model
    def default_subtypes(self, model_name):
        """ Retrieve the default subtypes (all, internal, external) for the given model. """
        subtype_ids, internal_ids, external_ids = self._default_subtypes(model_name)
        return self.browse(subtype_ids), self.browse(internal_ids), self.browse(external_ids)

    @tools.ormcache('self.env.uid', 'model_name')
    def _default_subtypes(self, model_name):
        domain = [('default', '=', True),
                  '|', ('res_model', '=', model_name), ('res_model', '=', False)]
        subtypes = self.search(domain)
        internal = subtypes.filtered('internal')
        return subtypes.ids, internal.ids, (subtypes - internal).ids
