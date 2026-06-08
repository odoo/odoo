from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo import fields
    from odoo.api import Environment

from .generator import Generator


class Boolean(Generator):
    """Generate random boolean values (``True``, ``False``, optionally ``None``)."""
    name = 'scalar.boolean'
    allowed_field_types = ('boolean', 'virtual')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.unique:
            # It makes little sense to have a unique constraint on a boolean field
            raise ValueError(self.env._("Unique cannot be used with the boolean generator."))

        possible_values = [True, False]
        if not self.field.required:
            possible_values.append(None)

        invalid_values = [v for v in self.values if v not in possible_values]
        if invalid_values:
            raise ValueError(self.env._(
                "Invalid values %(invalid_values)s for %(field_type)s field. "
                "Allowed values are: %(possible_values)s.",
                invalid_values=invalid_values,
                field_type=self.field.type,
                possible_values=possible_values,
            ))

        if not self.values:
            self.values = possible_values

    def _next(self, known_vals):
        return self.distribution.choice(self.values)


class Integer(Generator):
    """Generate random integers within a ``[start, end]`` range."""
    name = 'scalar.integer'
    allowed_field_types = ('integer', 'float', 'virtual')

    def __init__(self, start: int = 1, end: int = 1000000, **kwargs):
        super().__init__(**kwargs)
        self.start = start
        self.end = end

    def _next(self, known_vals):
        if self.values:
            return self.distribution.choice(self.values)

        return self.distribution.sample_discrete(self.start, self.end)

    @classmethod
    def convert_to_kwargs(cls, attrs):
        kwargs = super().convert_to_kwargs(attrs)
        kwargs.update(**{k: int(v) for k, v in attrs.items() if k in ('start', 'end')})
        return kwargs


class Float(Generator):
    """Generate random floats within a ``[start, end]`` range."""
    name = 'scalar.float'
    allowed_field_types = ('float', 'virtual')

    def __init__(self, start: float = 1.0, end: float = 1000000.0, **kwargs):
        super().__init__(**kwargs)
        self.start = start
        self.end = end

    def _next(self, known_vals):
        if self.values:
            return self.distribution.choice(self.values)

        return self.distribution.sample_continuous(self.start, self.end)

    @classmethod
    def convert_to_kwargs(cls, attrs):
        kwargs = super().convert_to_kwargs(attrs)
        kwargs.update(**{k: float(v) for k, v in attrs.items() if k in ('start', 'end')})
        return kwargs


class Monetary(Generator):
    """Generate random monetary values within a ``[start, end]`` range, rounded to the currency's precision."""
    name = 'scalar.monetary'
    allowed_field_types = ('monetary', 'virtual')

    def __init__(self, field: fields.Monetary, env: Environment, start: float = 1.0, end: float = 1000000.0, **kwargs):
        """Initialize monetary generation and depend on the field currency when available.

        :param field: Monetary field receiving generated values.
        :param env: Environment used to resolve the currency field.
        :param start: Lower bound for sampled monetary values.
        :param end: Upper bound for sampled monetary values.
        """
        self._validate_field_type(field)
        currency_field_name = field.get_currency_field(env[field.model_name])
        depends = [currency_field_name] if currency_field_name else None
        super().__init__(field=field, env=env, depends=depends, **kwargs)
        self.start = start
        self.end = end
        self.currency_field_name = currency_field_name

    def _next(self, known_vals):
        if self.values:
            value = self.distribution.choice(self.values)
        else:
            value = self.distribution.sample_continuous(self.start, self.end)

        currency_id = known_vals.get(self.currency_field_name)
        if currency_id:
            currency = self.env['res.currency'].browse(currency_id)
            value = round(value, currency.decimal_places)

        return value

    @classmethod
    def convert_to_kwargs(cls, attrs):
        kwargs = super().convert_to_kwargs(attrs)
        kwargs.update(**{k: float(v) for k, v in attrs.items() if k in ('start', 'end')})
        return kwargs
