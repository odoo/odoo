# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval, datetime


class IrFilters(models.Model):
    _name = 'ir.filters'
    _description = 'Filters'
    _order = 'model_id, name, id desc'

    name = fields.Char(string='Filter Name', required=True)
    user_id = fields.Many2one('res.users', string='User', ondelete='cascade')
    domain = fields.Text(default='[]', required=True)
    context = fields.Text(default='{}', required=True)
    sort = fields.Char(default='[]', required=True)
    model_id = fields.Selection(selection='_list_all_models', string='Model', required=True)
    is_default = fields.Boolean(string='Default Filter')
    action_id = fields.Many2one('ir.actions.actions', string='Action', ondelete='cascade',
                                help="The menu action this filter applies to. "
                                     "When left empty the filter applies to all menus "
                                     "for this model.")
    embedded_action_id = fields.Many2one('ir.embedded.actions', help="The embedded action this filter is applied to", ondelete="cascade")
    embedded_parent_res_id = fields.Integer(help="id of the record the filter should be applied to. Only used in combination with embedded actions")
    active = fields.Boolean(default=True)

    # Partial constraint, complemented by unique index (see below). Still
    # useful to keep because it provides a proper error message when a
    # violation occurs, as it shares the same prefix as the unique index.
    _name_model_uid_unique = models.Constraint(
        'UNIQUE (model_id, user_id, action_id, embedded_action_id, embedded_parent_res_id, name)',
        "Filter names must be unique",
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
    # Use unique index to implement unique constraint on the lowercase name (not possible using a constraint)
    _name_model_uid_unique_action_index = models.UniqueIndex(
        '(model_id, COALESCE(user_id, -1), COALESCE(action_id, -1), '
        'lower(name), embedded_parent_res_id, COALESCE(embedded_action_id,-1))',
    )

    @api.model
    def _list_all_models(self):
        lang = self.env.lang or 'en_US'
        self._cr.execute(
            "SELECT model, COALESCE(name->>%s, name->>'en_US') FROM ir_model ORDER BY 2",
            [lang],
        )
        return self._cr.fetchall()

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
        self.ensure_one()
        return safe_eval(self.domain, {
            'datetime': datetime,
            'context_today': datetime.datetime.now,
        })

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
            ``name``, ``is_default``, ``domain``, ``user_id`` (m2o tuple),
            ``action_id`` (m2o tuple), ``embedded_action_id`` (m2o tuple), ``embedded_parent_res_id``
            and ``context`` of the matching ``ir.filters``.
        """
        # available filters: private filters (user_id=uid) and public filters (uid=NULL),
        # and filters for the action (action_id=action_id) or global (action_id=NULL)
        user_context = self.env['res.users'].context_get()
        action_domain = self._get_action_domain(action_id, embedded_action_id, embedded_parent_res_id)
        return self.with_context(user_context).search_read(
            action_domain + [('model_id', '=', model), ('user_id', 'in', [self._uid, False])],
            ['name', 'is_default', 'domain', 'context', 'user_id', 'sort', 'embedded_action_id', 'embedded_parent_res_id'],
        )

    @api.model
    def _check_global_default(self, vals, matching_filters):
        """ _check_global_default(dict, list(dict), dict) -> None

        Checks if there is a global default for the model_id requested.

        If there is, and the default is different than the record being written
        (-> we're not updating the current global default), raise an error
        to avoid users unknowingly overwriting existing global defaults (they
        have to explicitly remove the current default before setting a new one)

        This method should only be called if ``vals`` is trying to set
        ``is_default``

        :raises odoo.exceptions.UserError: if there is an existing default and
                                            we're not updating it
        """
        domain = self._get_action_domain(vals.get('action_id'), vals.get('embedded_action_id'), vals.get('embedded_parent_res_id'))
        defaults = self.search(domain + [
            ('model_id', '=', vals['model_id']),
            ('user_id', '=', False),
            ('is_default', '=', True),
        ])

        if not defaults:
            return
        if matching_filters and (matching_filters[0]['id'] == defaults.id):
            return

        raise UserError(self.env._("There is already a shared filter set as default for %(model)s, delete or change it before setting a new default", model=vals.get('model_id')))

    @api.model
    def create_or_replace(self, vals):
        action_id = vals.get('action_id')
        embedded_action_id = vals.get('embedded_action_id')
        if not embedded_action_id and 'embedded_parent_res_id' in vals:
            del vals['embedded_parent_res_id']
        embedded_parent_res_id = vals.get('embedded_parent_res_id')
        current_filters = self.get_filters(vals['model_id'], action_id, embedded_action_id, embedded_parent_res_id)
        matching_filters = [f for f in current_filters
                            if f['name'].lower() == vals['name'].lower()
                            # next line looks for matching user_ids (specific or global), i.e.
                            # f.user_id is False and vals.user_id is False or missing,
                            # or f.user_id.id == vals.user_id
                            if (f['user_id'] and f['user_id'][0]) == vals.get('user_id')]

        if vals.get('is_default'):
            if vals.get('user_id'):
                # Setting new default: any other default that belongs to the user
                # should be turned off
                domain = self._get_action_domain(action_id, embedded_action_id, embedded_parent_res_id)
                defaults = self.search(domain + [
                    ('model_id', '=', vals['model_id']),
                    ('user_id', '=', vals['user_id']),
                    ('is_default', '=', True),
                ])
                if defaults:
                    defaults.write({'is_default': False})
            else:
                self._check_global_default(vals, matching_filters)

        # When a filter exists for the same (name, model, user) triple, we simply
        # replace its definition (considering action_id irrelevant here)
        if matching_filters:
            matching_filter = self.browse(matching_filters[0]['id'])
            matching_filter.write(vals)
            return matching_filter

        return self.create(vals)
