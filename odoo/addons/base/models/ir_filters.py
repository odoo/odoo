# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools.misc import clean_context


class IrFilters(models.Model):
    _name = 'ir.filters'
    _description = 'Filter'
    _order = 'model_id, name, id desc'

    name = fields.Char(string='Filter Name', required=True)
    user_ids = fields.Many2many('res.users', string='Users', ondelete='cascade', help="The users the filter is shared with. If empty, the filter is shared with all users.", context={'active_test': False})
    domain = fields.Text(default='[]', required=True)
    context = fields.Text(default='{}', required=True)
    sort = fields.Char(default='[]', required=True)
    model_id = fields.Selection(selection='_list_all_models', string='Model', required=True)
    is_default = fields.Boolean(string='Default Filter')
    action_id = fields.Many2one('ir.actions.actions', string='Action', ondelete='cascade',
                                help="The menu action this filter applies to. "
                                     "When left empty the filter applies to all menus "
                                     "for this model.")
    active = fields.Boolean(default=True)

    _get_filters_index = models.Index(
        '(model_id, action_id)',
    )
    _check_sort_json = models.Constraint(
        "CHECK(sort IS NULL OR jsonb_typeof(sort::jsonb) = 'array')",
        "Invalid sort definition",
    )

    def _sanitize_shared_context(self):
        for shared_filter in self.filtered(lambda f: f.user_ids != self.env.user and f.context.strip()):
            context = ast.literal_eval(shared_filter.context.strip())
            cleaned = clean_context(context)
            defaults = context.keys() - cleaned.keys()
            if defaults:
                shared_filter.context = repr(cleaned)

    @api.model
    def _list_all_models(self):
        lang = self.env.lang or 'en_US'
        self.env.cr.execute(
            "SELECT model, COALESCE(name->>%s, name->>'en_US') FROM ir_model ORDER BY 2",
            [lang],
        )
        return self.env.cr.fetchall()

    @api.model_create_multi
    def create(self, vals_list):
        filters = super().create(vals_list)
        filters._sanitize_shared_context()
        return filters

    def write(self, vals):
        new_filter = super().write(vals)
        self.check_access('write')
        if 'context' in vals or 'user_ids' in vals:
            self._sanitize_shared_context()
        return new_filter

    def _get_eval_domain(self) -> Domain:
        try:
            return Domain(ast.literal_eval(self.domain))
        except ValueError as e:
            raise ValueError(f"Invalid domain: {self.domain}") from e

    @api.model
    def _get_action_domain(self, action_id=None) -> Domain:
        """Return a domain component for matching filters that are visible in the
           same context (menu/view) as the given action."""
        return Domain('action_id', 'in', [action_id or False, False])

    @api.model
    def get_filters(self, model, action_id=None):
        """Obtain the list of filters available for the user on the given model.

        :param int model: id of model to find filters for
        :param action_id: optional ID of action to restrict filters to this action
            plus global filters. If missing only global filters are returned.
            The action does not have to correspond to the model, it may only be
            a contextual action.
        :return: list of :meth:`~osv.read`-like dicts containing the
            ``name``, ``is_default``, ``domain``, ``user_ids`` (m2m),
            ``action_id`` (m2o tuple) and ``context`` of the matching ``ir.filters``.
        """
        # available filters: private filters (user_ids=uids) and public filters (uids=NULL),
        # and filters for the action (action_id=action_id) or global (action_id=NULL)
        user_context = self.env['res.users'].context_get()
        action_domain = self._get_action_domain(action_id)
        return self.with_context(user_context).search_read(
            action_domain & Domain('model_id', '=', model) & Domain('user_ids', 'in', [self.env.uid, False]),
            ['name', 'is_default', 'domain', 'context', 'user_ids', 'sort'],
        )

    @api.model
    def create_filter(self, vals):
        return self.create(vals)
