from __future__ import annotations

from ast import literal_eval
from datetime import date, datetime, timedelta
from string import ascii_letters, digits
from typing import TYPE_CHECKING, cast

from odoo import fields

from .generator import Generator

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from ..utils.distributions import Distribution


class PropertyDefinition(Generator):
    """
    Generate a properties definition list for a ``properties_definition`` field.

    Either assembles definitions from explicit virtual-field ``props``, or randomly
    generates ``count`` property entries with types drawn from ``allowed_types``.
    """
    name = 'properties.definition'
    allowed_field_types = ('properties_definition',)

    def __init__(
        self,
        props: Sequence[str] | None = None,
        count: int | None = None,
        allowed_types: Collection[str] | None = None,
        possible_values: dict[str, Sequence[str]] | None = None,
        **kwargs,
    ):
        """Initialize property-definition generation.

        :param props: Virtual field names that provide explicit property definitions.
        :param count: Number of random property definitions to create when
            ``props`` is not provided.
        :param allowed_types: Property types eligible for random definitions.
        :param possible_values: Values used for generated ``selection`` and ``tags`` properties.
        """
        env = kwargs['env']
        if props and (count or allowed_types or possible_values):
            raise ValueError(env._(
                "If `props` are provided, neither `count` or `allowed_types` or `possible_values` can be set.",
            ))

        # If props are provided, implicitly add them to the depends
        depends = list(props) if props else None

        super().__init__(depends=depends, **kwargs)

        # props is a list of virtual field names that define individual properties
        self.props = props
        self.count = count
        self.allowed_types = allowed_types or fields.Properties.ALLOWED_TYPES
        if not props and any(type_ in ('selection', 'tags') for type_ in self.allowed_types) and not possible_values:
            raise ValueError(self.env._(
                "`possible_values` must be provided when `allowed_types` includes 'selection' or 'tags'. ",
            ))

        self.possible_values = possible_values

    def _next(self, known_vals):
        definition = []

        # User explicitly defined Virtual fields for the props
        if self.props:
            for prop_fname in self.props:
                prop_def = known_vals[prop_fname]
                if prop_def:  # Skip None/False values
                    if not prop_def.get('name'):
                        prop_def['name'] = fields.Properties.generate_property_name()

                    definition.append(prop_def)

        # Fallback: User doesn't care about specific values -> Random generation
        else:
            for i in range(self.count):
                prop_type = self.distribution.choice(self.allowed_types)

                prop = {
                    'name': fields.Properties.generate_property_name(),
                    'string': f'Prop {i} {prop_type}',
                    'type': prop_type,
                }

                if prop_type == 'selection':
                    prop['selection'] = [
                        (str(j), val) for j, val in enumerate(self.possible_values)
                    ]
                elif prop_type == 'tags':
                    prop['tags'] = [
                        (f't{j}', val, self.distribution.sample_discrete(1, 11))
                        for j, val in enumerate(self.possible_values)
                    ]

                definition.append(prop)

        return definition

    @classmethod
    def convert_to_kwargs(cls, attrs):
        kwargs = super().convert_to_kwargs(attrs)

        if 'count' in attrs:
            kwargs['count'] = int(attrs['count'])

        if 'allowed_types' in attrs:
            kwargs['allowed_types'] = literal_eval(attrs['allowed_types'])

        if 'possible_values' in attrs:
            kwargs['possible_values'] = literal_eval(attrs['possible_values'])

        if 'entries' in attrs:
            kwargs['entries'] = literal_eval(attrs['entries'])

        return kwargs


class PropertyProp(Generator):
    """
    Generate a single property definition entry for use with ``PropertyDefinition``.

    Intended for virtual fields that feed into a ``properties.definition`` generator
    via its ``props`` parameter.
    """
    name = 'properties.prop'
    allowed_field_types = ('virtual',)

    def __init__(self, prop_type: str, string: str, possible_values: Sequence[str] | None = None, **kwargs):
        """Initialize a virtual property-definition entry.

        :param prop_type: Odoo property type for the generated definition.
        :param string: User-facing label stored on the property definition.
        :param possible_values: Values required by ``selection`` and ``tags`` properties.
        """
        super().__init__(**kwargs)
        if prop_type not in fields.Properties.ALLOWED_TYPES:
            raise ValueError(self.env._(
                "`prop_type` expected to be in fields.Properties.ALLOWED_TYPES '%(allowed)s'. "
                "Got %(actual)s instead.",
                allowed=fields.Properties.ALLOWED_TYPES,
                actual=prop_type,
            ))

        self.prop_type = prop_type
        self.string = string
        # Nobody is expecting this technical generator to potentially return False.
        self.null_ratio = 0

        if prop_type in ('selection', 'tags') and not possible_values:
            raise ValueError(self.env._(
                "`possible_values` must be provided for prop_type '%(prop_type)s' "
                "in generator %(generator_name)s of field %(field_name)s",
                prop_type=self.prop_type,
                generator_name=self.name,
                field_name=self.field.name,
            ))

        prop = {
            'name': fields.Properties.generate_property_name(),
            'string': string,
            'type': prop_type,
        }

        if prop_type == 'selection':
            prop['selection'] = [
                (str(i), val) for i, val in enumerate(possible_values)
            ]
        elif prop_type == 'tags':
            prop['tags'] = [
                (f't{i}', val, self.distribution.sample_discrete(1, 11))
                for i, val in enumerate(possible_values)
            ]

        self.prop = prop

    def _next(self, known_vals):
        return self.prop

    @classmethod
    def convert_to_kwargs(cls, attrs):
        kwargs = super().convert_to_kwargs(attrs)

        if 'prop_type' in attrs:
            kwargs['prop_type'] = attrs['prop_type']

        if 'string' in attrs:
            kwargs['string'] = attrs['string']

        if 'possible_values' in attrs:
            kwargs['possible_values'] = literal_eval(attrs['possible_values'])

        return kwargs


def _random_value(prop, distribution: Distribution):
    """Generate a value compatible with a property definition entry.

    :param prop: Property definition dictionary from a properties definition field.
    :param distribution: Distribution used for scalar sampling and choices.
    :return: A value suitable for ``prop['type']``.
    """
    match prop['type']:
        case 'boolean':
            return distribution.choice([True, False])
        case 'integer':
            return distribution.sample_discrete(0, 100)
        case 'float':
            return distribution.sample_continuous(0, 100)
        case 'char' | 'text':
            return ''.join(distribution.choices(ascii_letters + digits, k=12))
        case 'selection':
            options = prop['selection']
            return distribution.choice(options)[0]
        case 'tags':
            tags = prop['tags']
            k = distribution.sample_discrete(0, len(tags))
            return [t[0] for t in distribution.pick(tags, k)]
        case 'date':
            return (
                date.today()
                - timedelta(days=distribution.sample_discrete(0, 365))
            ).isoformat()
        case 'datetime':
            return (
                datetime.now()
                - timedelta(days=distribution.sample_discrete(0, 365))
            ).isoformat()
        case _:
            return None


class PropertyValue(Generator):
    """
    Generate property values matching the definition on the parent container record.

    Depends on the container field; fills each defined property with a random
    type-appropriate value unless overridden by a matching virtual field.
    """
    name = 'properties.value'
    allowed_field_types = ('properties',)

    def __init__(self, field: fields.Properties, **kwargs):
        """Initialize property-value generation from the container's definitions.

        :param field: Properties field receiving generated values.
        """
        # Validate early to be able to read on `definition_record`
        self._validate_field_type(field)
        # Automatically add the container field (e.g. parent_id) to dependencies,
        # so it is generated before we try to read definitions from it.
        super().__init__(field=field, depends=[field.definition_record], null_ratio=0, **kwargs)
        self.field = cast('fields.Properties', self.field)

    def _next(self, known_vals):
        container_id = known_vals[self.field.definition_record]
        if not container_id:
            return {}

        container_model_name = self.env[self.field.model_name]._fields[self.field.definition_record].comodel_name
        container = self.env[container_model_name].browse(container_id)

        definitions = container[self.field.definition_record_field]

        if not definitions:
            return {}

        values = {}
        for prop in definitions:
            # User defined a Virtual Field with a Label (e.g. "Age")
            # Match on the `string` of the property, as it is human-readable,
            # instead of the `name`.
            if prop['string'] in known_vals:
                values[prop['name']] = known_vals[prop['string']]
                continue

            # Fallback: User doesn't care about content
            # -> Random generation
            values[prop['name']] = _random_value(prop, self.distribution)

        return values
