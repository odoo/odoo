from __future__ import annotations

import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..utils import loading, xml
from ..utils.orm import get_model_method

DEFINITION_PREFETCH_GROUP = 'Definitions'


class Blueprint(models.Model):
    """
    Declarative definition of what synthetic data to create.

    A blueprint holds an XML or JSON definition describing which models to
    populate, how many records to create, and which generators to use for
    each field.  It supports simple inheritance via ``inherit_id``
    (XPath specs applied to the parent's XML).

    Blueprints are instantiated into ``populate.job`` records
    within a ``populate.session`` at execution time.
    """
    _name = 'populate.blueprint'
    _description = 'Data Population Blueprint'
    _parent_name = 'inherit_id'

    name = fields.Char("Blueprint Name", required=True)
    inherit_id = fields.Many2one(
        comodel_name='populate.blueprint',
        string='Inherited Blueprint',
        ondelete='set null',
        index=True,
        help="Blueprint to inherit from. Use XPath expressions in definition_xml to modify the parent.",
    )
    definition_xml = fields.Char("Raw XML Definition", prefetch=DEFINITION_PREFETCH_GROUP)
    definition_json = fields.Json("Raw JSON Definition", prefetch=DEFINITION_PREFETCH_GROUP)
    definition = fields.Json(
        string="JSON Definition",
        compute='_compute_definition',
        prefetch=DEFINITION_PREFETCH_GROUP,
        readonly=True,
    )

    _has_definition = models.Constraint(
        'CHECK(definition_xml IS NOT NULL OR definition_json IS NOT NULL)',
        "Either XML or JSON definition must be provided",
    )

    @api.constrains('definition_xml', 'definition_json', 'inherit_id')
    def _check_definition(self):  # TODO: simplify by using JsonSchema validation
        """Validate resolved blueprint definitions against the loaded models.

        Checks inheritance cycles, operation blocks, model names, and field names before
        a session can instantiate jobs from the blueprint.
        """
        if self._has_cycle():
            raise ValidationError(self.env._("You cannot create recursive inherited blueprints."))

        exceptions = []

        def fail(blueprint, block, reason):
            exceptions.append(ValidationError(self.env._(
                "Blueprint '%(blueprint)s': %(reason)s\n"
                "Definition that failed:\n%(definition)s",
                blueprint=blueprint.name,
                reason=reason,
                definition=json.dumps(block, indent=2),
            )))

        for blueprint in self:
            for block in blueprint.definition:
                operation = block.get('operation')
                if not operation:
                    fail(blueprint, block, self.env._("Missing 'operation'."))
                    continue  # The operation decides which id/ref/domain rules apply.

                if operation not in ('create', 'write', 'function'):
                    fail(blueprint, block, self.env._("Unknown operation '%(operation)s'.", operation=operation))
                    continue  # Unknown operations have no validation rules.

                if operation == 'create' and 'ref' in block:
                    fail(blueprint, block, self.env._("Create blocks use 'id', not 'ref'."))

                if operation == 'write' and 'id' in block:
                    fail(blueprint, block, self.env._("Write blocks use 'ref', not 'id'."))

                if operation == 'function' and 'id' in block:
                    fail(blueprint, block, self.env._("Function blocks use 'ref', not 'id'."))

                if operation == 'create' and 'batched' in block:
                    fail(blueprint, block, self.env._("Create blocks cannot define 'batched'."))

                if operation == 'function' and not block.get('name'):
                    fail(blueprint, block, self.env._("Function blocks require 'name'."))

                if operation == 'function' and block.get('fields'):
                    fail(blueprint, block, self.env._("Function blocks use 'arg', not 'field'."))

                if operation in ('create', 'write') and block.get('args'):
                    fail(blueprint, block, self.env._(
                        "%(operation)s blocks cannot define 'arg'.",
                        operation=operation.capitalize(),
                    ))

                if 'model' not in block:
                    fail(blueprint, block, self.env._("Missing 'model'."))
                    continue  # Field validation needs a model to resolve ORM fields.

                model_name = block['model']
                if model_name not in self.env:
                    fail(blueprint, block, self.env._("Unknown model '%(model)s'.", model=model_name))
                    continue  # The model registry lookup below is only safe for loaded models.

                model_field_names = self.env[model_name]._fields.keys()
                unknown_fields = [
                    field_name
                    for field_name in block.get('fields', {})
                    if field_name not in model_field_names
                ]
                if unknown_fields:
                    fail(blueprint, block, self.env._(
                        "Unknown field(s) on '%(model)s': %(fields)s.",
                        model=model_name,
                        fields=', '.join(repr(field) for field in unknown_fields),
                    ))

                if operation == 'function':
                    method_name = block.get('name')
                    method = get_model_method(self.env[model_name], method_name)
                    if method is None:
                        fail(blueprint, block, self.env._(
                            "Unknown or non-callable method '%(method)s' on '%(model)s'.",
                            method=method_name,
                            model=model_name,
                        ))

                target_names_by_kind = {
                    'fields': set(block.get('fields', {})),
                    'values': set(block.get('values', {})),
                    'args': set(block.get('args', {})),
                }
                duplicate_names = (
                    target_names_by_kind['fields'] & target_names_by_kind['values']
                    | target_names_by_kind['fields'] & target_names_by_kind['args']
                    | target_names_by_kind['values'] & target_names_by_kind['args']
                )
                if duplicate_names:
                    fail(blueprint, block, self.env._(
                        "Names used for multiple generated targets: %(names)s.",
                        names=', '.join(repr(name) for name in sorted(duplicate_names)),
                    ))

                positional_arg_indexes = sorted(
                    int(name)
                    for name in target_names_by_kind['args']
                    if name.isdecimal()
                )
                if positional_arg_indexes and positional_arg_indexes != list(range(len(positional_arg_indexes))):
                    fail(blueprint, block, self.env._(
                        "Positional arg names must be contiguous indexes from '0'.",
                    ))
        if exceptions:
            # The module doesn't have a webclient interface, so it's ok to not raise an explicit ValidationError
            raise ExceptionGroup(self.env._("Some blueprint definition(s) are invalid."), exceptions)

    @api.depends('definition_xml', 'definition_json')
    def _compute_definition(self):
        """Compute the blueprint's definition in JSON.

        If both raw definitions are specified, the XML one takes precedence.
        If inherit_id is set, apply inheritance specs first.
        """
        for blueprint in self:
            resolved_definition = blueprint._get_resolved_definition()
            if resolved_definition:
                blueprint.definition = xml.parse(resolved_definition)
            else:
                blueprint.definition = blueprint.definition_json

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if definition_xml := vals.get('definition_xml'):
                vals['definition_xml'] = xml.ensure_root(definition_xml)
        return super().create(vals_list)

    def write(self, vals):
        if definition_xml := vals.get('definition_xml'):
            vals['definition_xml'] = xml.ensure_root(definition_xml)
        return super().write(vals)

    def _get_resolved_definition(self):
        """Get the resolved XML definition, applying inheritance specs if needed.

        :return: XML definition string, or ``None`` for JSON-only blueprints.
        :raise ValueError: If inheritance targets a JSON-only parent or invalid XPath specs.
        """
        self.ensure_one()

        if not self.definition_xml:
            return None

        if not self.inherit_id:
            return self.definition_xml

        parent_definition_xml = self.inherit_id._get_resolved_definition()
        if not parent_definition_xml:
            raise ValueError(self.env._(
                "The blueprint '%(parent)s' does not have an XML definition, but '%(child)s' inherit from it.",
                parent=self.inherit_id.name,
                child=self.name,
            ))

        try:
            return xml.apply_inheritance(parent_definition_xml, self.definition_xml)
        except ValueError as e:
            raise ValueError(self.env._(
                "Error applying blueprint inheritance from %(parent)s' to %(child)s: %(error)s",
                parent=self.inherit_id.name,
                child=self.name,
                error=e,
            ))

    def _register_hook(self):
        """Load populate data if the `populate` module was installed or upgraded."""
        super()._register_hook()
        if 'populate' in self.env.registry.updated_modules:
            loading.load_populate(self.env)
