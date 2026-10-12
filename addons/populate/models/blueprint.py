from __future__ import annotations

import json
import re

from lxml import etree

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..utils import loading, xml
from ..utils.orm import get_model_method

DEFINITION_PREFETCH_GROUP = 'Definitions'
_IMPORT_NAMESPACE_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_-]*$')


class Blueprint(models.Model):
    """
    Declarative definition of what synthetic data to create.

    A blueprint holds an XML or JSON definition describing which models to
    populate, how many records to create, and which generators to use for
    each field. It supports inheritance via ``inherit_id`` and reusable XML
    composition via ``<import>`` blocks.

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
    def _check_definition(self):
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
            created_refs = set()
            for block in blueprint.definition:
                operation = block.get('operation')
                if not operation:
                    fail(blueprint, block, self.env._("Missing 'operation'."))
                    continue  # The operation decides which id/ref/domain rules apply.

                if operation not in ('create', 'write', 'function'):
                    fail(blueprint, block, self.env._("Unknown operation '%(operation)s'.", operation=operation))
                    continue  # Unknown operations have no validation rules.

                if operation == 'create' and (block_id := block.get('id')):
                    if block_id in created_refs:
                        fail(blueprint, block, self.env._(
                            "Create reference '%(ref)s' is declared more than once.",
                            ref=block_id,
                        ))
                    else:
                        created_refs.add(block_id)

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

    @api.depends('definition_xml', 'definition_json', 'inherit_id')
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
        result = super().write(vals)
        if {'definition_xml', 'definition_json', 'inherit_id'} & vals.keys():
            # Import dependencies live in the raw XML, so the ORM cannot infer
            # which computed definitions depend on the changed blueprints.
            self.env['populate.blueprint'].invalidate_model(['definition'])
        return result

    @api.ondelete(at_uninstall=False)
    def _invalidate_definition_cache(self):
        # Import dependencies are not ORM fields, so deleting an imported
        # blueprint must invalidate the cached definitions of its callers.
        self.env['populate.blueprint'].invalidate_model(['definition'])

    def _get_resolved_definition(self):
        """Resolve inheritance and expand imports into a concrete XML definition."""
        self.ensure_one()

        def resolve(blueprint, seen):
            if blueprint.id in seen:
                raise ValueError(self.env._(
                    "Recursive blueprint composition detected for '%(blueprint)s'.",
                    blueprint=blueprint.name,
                ))
            if not blueprint.definition_xml:
                return None

            seen |= {blueprint.id}
            if not blueprint.inherit_id:
                definition = etree.fromstring(blueprint.definition_xml)
            else:
                parent = resolve(blueprint.inherit_id, seen)
                if parent is None:
                    raise ValueError(self.env._(
                        "The blueprint '%(parent)s' does not have an XML definition, but '%(child)s' inherits from it.",
                        parent=blueprint.inherit_id.name,
                        child=blueprint.name,
                    ))
                try:
                    definition = xml.apply_inheritance_specs(
                        parent,
                        etree.fromstring(blueprint.definition_xml),
                    )
                except (ValueError, ValidationError) as error:
                    raise ValueError(self.env._(
                        "Error applying blueprint inheritance from '%(parent)s' to '%(child)s': %(error)s",
                        parent=blueprint.inherit_id.name,
                        child=blueprint.name,
                        error=error,
                    )) from error

            return xml.expand_imports(definition, lambda element: import_fragment(element, seen))

        def import_fragment(element, seen):
            unknown_attributes = set(element.attrib) - {'ref', 'as'}
            if unknown_attributes:
                raise ValueError(self.env._(
                    "Unknown <import> attribute(s): %(attributes)s.",
                    attributes=', '.join(sorted(unknown_attributes)),
                ))
            if (
                element.text and element.text.strip()
                or any(child.tail and child.tail.strip() for child in element)
            ):
                raise ValueError(self.env._("<import> may only contain inheritance specifications."))

            import_ref = element.get('ref')
            if not import_ref or '.' not in import_ref:
                raise ValueError(self.env._("<import> requires a fully qualified XML ID in 'ref'."))

            namespace = element.get('as')
            if 'as' in element.attrib and not namespace:
                raise ValueError(self.env._("An import namespace cannot be empty."))
            if namespace and not _IMPORT_NAMESPACE_RE.fullmatch(namespace):
                raise ValueError(self.env._("Invalid import namespace '%(namespace)s'.", namespace=namespace))

            imported_blueprint = self.env.ref(import_ref, raise_if_not_found=False)
            if not imported_blueprint:
                raise ValueError(self.env._("Imported blueprint '%(import_ref)s' was not found.", import_ref=import_ref))
            if imported_blueprint._name != self._name:
                raise ValueError(self.env._(
                    "'%(import_ref)s' refers to '%(model)s', not a populate blueprint.",
                    import_ref=import_ref,
                    model=imported_blueprint._name,
                ))

            imported = resolve(imported_blueprint, seen)
            if imported is None:
                raise ValueError(self.env._("Imported blueprint '%(import_ref)s' must use XML.", import_ref=import_ref))
            if len(element):
                imported = xml.apply_inheritance_specs(imported, element)
                imported = xml.expand_imports(
                    imported,
                    lambda nested: import_fragment(nested, seen | {imported_blueprint.id}),
                )

            if namespace:
                xml.namespace_references(imported, namespace)
            return imported

        definition = resolve(self, frozenset())
        return etree.tostring(definition, encoding='unicode') if definition is not None else None

    def _register_hook(self):
        """Load populate data if the `populate` module was installed or upgraded."""
        super()._register_hook()
        if 'populate' in self.env.registry.updated_modules:
            loading.load_populate(self.env)
