from odoo import api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.service import api_scope


class ResUsersApikeysScope(models.Model):
    """What a door lets an API key do: the models it reaches, the operations
    on each, the fields it never sees, the depth a path may cross. A route
    names one (`auth="bearer", scope="mcp"`), a key may be bound to one, and
    `service.model.call_kw` enforces it on every door alike."""

    _name = "res.users.apikeys.scope"
    _description = "API Key Scope"
    _order = "key"
    _rec_name = "name"

    name = fields.Char(required=True)
    key = fields.Char(
        required=True,
        help="The identifier a route declares (`scope=`) and a key is bound to; "
        "the string clients passed before scopes were records.",
    )
    active = fields.Boolean(default=True)
    line_ids = fields.One2many(
        comodel_name="res.users.apikeys.scope.line",
        inverse_name="scope_id",
        string="Models",
        help="The models this scope reaches, with what may be done on each. "
        "Empty: every model the key's user may reach, every operation, "
        "nothing hidden -- unless the scope is closed when empty.",
    )
    door_only = fields.Boolean(
        help="A key of this scope opens its door and nothing else: at the "
        "universal RPC doors it reaches no model at all. For a door whose "
        "calls are not model calls -- a DAV client, a device protocol.",
    )
    closed_when_empty = fields.Boolean(
        help="With no model line, a key of this scope reaches no model rather "
        "than every model. For a door whose module mints its keys: they reach "
        "what an operator names, and nothing before.",
    )
    max_depth = fields.Integer(
        default=8,
        help="How many relations a field path (a domain, an order, a read "
        "specification) may cross; a longer one is refused rather than "
        "checked in part.",
    )
    budget_requests = fields.Integer(
        help="Calls a key may make per window on this scope; 0 for no budget."
    )
    budget_window_seconds = fields.Integer(default=60)

    _key_uniq = models.Constraint("UNIQUE(key)", "A scope's key is its identity.")

    @api.constrains("max_depth", "budget_requests", "budget_window_seconds")
    def _check_bounds(self):
        for scope in self:
            if scope.max_depth <= 0:
                raise ValidationError(
                    self.env._("A scope's path depth must be at least 1.")
                )
            if scope.budget_requests < 0 or scope.budget_window_seconds <= 0:
                raise ValidationError(
                    self.env._("A scope's budget is a count over a positive window.")
                )

    @api.model
    def _get(self, key: str):
        return (
            self.sudo()
            .with_context(active_test=False)
            .search([("key", "=", key)], limit=1)
        )

    @api.model
    def _get_or_create(self, key: str):
        """The scope a key string names; one is made for a string no record
        carries yet, reaching everything, so a key generated for a door that
        was never described keeps working as it did."""
        scope = self._get(key)
        if not scope:
            scope = self.sudo().create({"name": key, "key": key})
        return scope

    @tools.ormcache("self.id")
    def _rules(self) -> api_scope.ScopeRules:
        self.check_singleton()
        if self.door_only:
            return api_scope.ScopeRules(
                key=self.key, models={}, max_depth=self.max_depth
            )
        lines = self.sudo().line_ids
        if not lines:
            return api_scope.ScopeRules(
                key=self.key,
                models={} if self.closed_when_empty else None,
                max_depth=self.max_depth,
            )
        return api_scope.ScopeRules(
            key=self.key,
            models={
                line.model_id.model: api_scope.ModelRule(
                    read=line.allow_read,
                    create=line.allow_create,
                    write=line.allow_write,
                    unlink=line.allow_unlink,
                    call=line.allow_call,
                    denied=frozenset(line.denied_field_ids.mapped("name")),
                )
                for line in lines
            },
            max_depth=self.max_depth,
        )

    @api.model_create_multi
    def create(self, vals_list):
        """Upserts on `key`: a module's data record for a door that a
        migration or `_get_or_create` already made a row for takes that row,
        so the xml id binds to it instead of tripping the key's uniqueness."""
        ids = [None] * len(vals_list)
        to_create = []
        for index, vals in enumerate(vals_list):
            existing = self._get(vals["key"]) if vals.get("key") else None
            if existing:
                existing.write({k: v for k, v in vals.items() if k != "key"})
                ids[index] = existing.id
            else:
                to_create.append((index, vals))
        if to_create:
            created = super().create([vals for _index, vals in to_create])
            for (index, _vals), scope in zip(to_create, created, strict=True):
                ids[index] = scope.id
        self.env.registry.clear_cache()
        return self.browse(ids)

    def write(self, vals):
        result = super().write(vals)
        self.env.registry.clear_cache()
        return result

    def unlink(self):
        result = super().unlink()
        self.env.registry.clear_cache()
        return result


class ResUsersApikeysScopeLine(models.Model):
    _name = "res.users.apikeys.scope.line"
    _description = "API Key Scope Model"
    _rec_name = "model_id"
    _order = "scope_id, model_id"

    scope_id = fields.Many2one(
        comodel_name="res.users.apikeys.scope",
        index=True,
        required=True,
        ondelete="cascade",
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        index=True,
        required=True,
        ondelete="cascade",
    )
    model_name = fields.Char(related="model_id.model")
    allow_read = fields.Boolean(default=True)
    allow_create = fields.Boolean()
    allow_write = fields.Boolean()
    allow_unlink = fields.Boolean()
    allow_call = fields.Boolean(
        help="Any public method that is not a read, a create, a write or an "
        "unlink: an action, a workflow verb."
    )
    denied_field_ids = fields.Many2many(
        comodel_name="ir.model.fields",
        string="Hidden Fields",
        domain="[('model_id', '=', model_id)]",
        help="Fields this scope never reads, writes, filters on or sorts by, "
        "and every field whose value derives from one of them.",
    )
    notes = fields.Text()

    _scope_model_uniq = models.Constraint(
        "UNIQUE(scope_id, model_id)", "A scope reaches a model once."
    )

    @api.constrains("denied_field_ids", "model_id")
    def _check_denied_fields_belong_to_the_model(self):
        for line in self:
            foreign = line.denied_field_ids.filtered(
                lambda f, line=line: f.model_id != line.model_id
            )
            if foreign:
                raise ValidationError(
                    self.env._(
                        "%(fields)s do not belong to %(model)s.",
                        fields=", ".join(foreign.mapped("name")),
                        model=line.model_id.model,
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        self.env.registry.clear_cache()
        return lines

    def write(self, vals):
        result = super().write(vals)
        self.env.registry.clear_cache()
        return result

    def unlink(self):
        result = super().unlink()
        self.env.registry.clear_cache()
        return result


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def _search_display_name_match(self, operator, value, search_fnames):
        return super()._search_display_name_match(
            operator,
            value,
            api_scope.visible_name_search_fields(self.env, self._name, search_fnames),
        )

    @api.model
    def _search_display_name_unset(self, search_fnames, negative):
        return super()._search_display_name_unset(
            api_scope.visible_name_search_fields(self.env, self._name, search_fnames),
            negative,
        )
