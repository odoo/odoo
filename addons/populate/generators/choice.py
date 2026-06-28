from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from odoo import fields

from .generator import Generator


class Sample(Generator):
    """Randomly pick from a required list of user-provided values."""
    name = 'choice.sample'
    allowed_field_types = (
        'integer', 'float',
        'char', 'text', 'html',
        'date', 'datetime',
        'boolean',
        'selection',
        'virtual',
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if not self.values:
            raise ValueError(self.env._("Values cannot be empty for the %s generator.", self.name))

    def _next(self, known_vals):
        return self.distribution.choice(self.values)


class Selection(Generator):
    """Randomly pick from the selection field's possible values."""
    name = 'choice.selection'
    allowed_field_types = ('selection',)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.field = cast('fields.Selection', self.field)

        if self.unique:
            # It makes little sense to have a unique constraint on a selection field
            raise ValueError(self.env._("Unique cannot be used with the selection generator."))

        possible_values = self.field.get_values(self.env)

        invalid_values = [v for v in self.values if v not in possible_values]
        if invalid_values:
            raise ValueError(self.env._(
                "Invalid values %(invalid)s for selection field. Allowed values are: %(possible)s.",
                invalid=invalid_values,
                possible=possible_values,
            ))

        if not self.values:
            self.values = possible_values

    def _next(self, known_vals):
        return self.distribution.choice(self.values)
