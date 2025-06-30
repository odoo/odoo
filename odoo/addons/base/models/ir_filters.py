# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast

from odoo import api, fields, models


class IrFilters(models.Model):
    _name = 'ir.filters'
    _description = 'Filters'
    _order = 'model_id, name, id desc'

    name = fields.Char(string='Filter Name', required=True)
    user_ids = fields.Many2many('res.users', string='Users', ondelete='cascade', help="The users the filter is shared with. If empty, the filter is shared with all users.")
    domain = fields.Text(default='[]', required=True)
    context = fields.Text(default='{}', required=True)
    sort = fields.Char(default='[]', required=True)
    model_id = fields.Selection(selection='_list_all_models', string='Model', required=True)
    is_default = fields.Boolean(string='Default Filter')
    action_id = fields.Many2one('ir.actions.actions', string='Action', ondelete='cascade',
                                help="The menu action this filter applies to. "
                                     "When left empty the filter applies to all menus "
                                     "for this model.")
    embedded_action_id = fields.Many2one('ir.embedded.actions', help="The embedded action this filter is applied to", ondelete="cascade", index='btree_not_null')
    embedded_parent_res_id = fields.Integer(help="id of the record the filter should be applied to. Only used in combination with embedded actions")
    active = fields.Boolean(default=True)

    _get_filters_index = models.Index(
        '(model_id, action_id, embedded_action_id, embedded_parent_res_id)',
    )
    # The embedded_parent_res_id can only be defined when the embedded_action_id field is set.
    # As the embedded model is linked to only one res_model, It ensure the unicity of the filter regarding the
    # embedded_parent_res_model and the embedded_parent_res_id
    _check_res_id_only_when_embedded_action = models.Constraint(
        'CHECK(NOT (embedded_parent_res_id IS NOT NULL AND embedded_action_id IS NULL))',
        "Constraint to ensure that the embedded_parent_res_id is only defined when a top_action_id is defined.",
    )
    _check_sort_json = models.Constraint(
        "CHECK(sort IS NULL OR jsonb_typeof(sort::jsonb) = 'array')",
        "Invalid sort definition",
    )

    @api.model
    def _list_all_models(self):
        lang = self.env.lang or 'en_US'
        self.env.cr.execute(
            "SELECT model, COALESCE(name->>%s, name->>'en_US') FROM ir_model ORDER BY 2",
            [lang],
        )
        return self.env.cr.fetchall()

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        # NULL Integer field value read as 0, wouldn't matter except in this case will trigger
        # check_res_id_only_when_embedded_action
        for vals in vals_list:
            if vals.get('embedded_parent_res_id') == 0:
                del vals['embedded_parent_res_id']
        return [dict(vals, name=self.env._("%s (copy)", ir_filter.name)) for ir_filter, vals in zip(self, vals_list)]

    def write(self, vals):
        new_filter = super().write(vals)
        self.check_access('write')
        return new_filter

    def _get_eval_domain(self):
        try:
            return ast.literal_eval(self.domain)
        except ValueError as e:
            raise ValueError("Invalid domain: {self.domain}") from e

    @api.model
    def _get_action_domain(self, action_id=None, embedded_action_id=None, embedded_parent_res_id=None):
        """Return a domain component for matching filters that are visible in the
           same context (menu/view) as the given action."""
        action_condition = ('action_id', 'in', [action_id, False]) if action_id else ('action_id', '=', False)
        embedded_condition = ('embedded_action_id', '=', embedded_action_id) if embedded_action_id else ('embedded_action_id', '=', False)
        embedded_parent_res_id_condition = ('embedded_parent_res_id', '=', embedded_parent_res_id) if embedded_action_id and embedded_parent_res_id else ('embedded_parent_res_id', 'in', [0, False])

        return [action_condition, embedded_condition, embedded_parent_res_id_condition]

    @api.model
    def get_filters(self, model, action_id=None, embedded_action_id=None, embedded_parent_res_id=None):
        """Obtain the list of filters available for the user on the given model.

        :param int model: id of model to find filters for
        :param action_id: optional ID of action to restrict filters to this action
            plus global filters. If missing only global filters are returned.
            The action does not have to correspond to the model, it may only be
            a contextual action.
        :return: list of :meth:`~osv.read`-like dicts containing the
            ``name``, ``is_default``, ``domain``, ``user_ids`` (m2m),
            ``action_id`` (m2o tuple), ``embedded_action_id`` (m2o tuple), ``embedded_parent_res_id``
            and ``context`` of the matching ``ir.filters``.
        """
        # available filters: private filters (user_ids=uids) and public filters (uids=NULL),
        # and filters for the action (action_id=action_id) or global (action_id=NULL)
        user_context = self.env['res.users'].context_get()
        action_domain = self._get_action_domain(action_id, embedded_action_id, embedded_parent_res_id)
        return self.with_context(user_context).search_read(
            action_domain + [('model_id', '=', model), ('user_ids', 'in', [self.env.uid, False])],
            ['name', 'is_default', 'domain', 'context', 'user_ids', 'sort', 'embedded_action_id', 'embedded_parent_res_id'],
        )

    @api.model
    def create_filter(self, vals):
        embedded_action_id = vals.get('embedded_action_id')
        if not embedded_action_id and 'embedded_parent_res_id' in vals:
            del vals['embedded_parent_res_id']
        return self.create(vals)
