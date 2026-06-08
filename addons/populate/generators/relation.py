from __future__ import annotations

from typing import TYPE_CHECKING

from odoo import Command
from odoo.fields import Domain

from ..utils import clamp
from ..utils.orm import DynamicDomain
from .generator import ComodelGenerator

if TYPE_CHECKING:
    from odoo.api import DomainType


class RelationOne(ComodelGenerator):
    """Pick a random existing record ID from the comodel for Many2one fields."""
    name = 'relation.one'
    allowed_field_types = ('many2one', 'virtual')

    def __init__(
        self,
        domain: DomainType | DynamicDomain | None = None,
        comodel_name: str | None = None,
        **kwargs,
    ):
        """Initialize a relation generator and infer dynamic-domain dependencies.

        :param domain: Static domain or dynamic domain evaluated per generated record.
        :param comodel_name: Explicit comodel name, required for virtual fields.
        """
        depends: list[str] = kwargs.pop('depends', [])
        if isinstance(domain, DynamicDomain):
            depends.extend(domain.dynamic_fields)

        super().__init__(depends=depends, **kwargs)

        if self.field.type == 'virtual' and not comodel_name:
            raise ValueError(self.env._("'comodel_name' needs to be provided for virtual fields."))

        comodel_name = self.field.comodel_name or comodel_name

        if comodel_name not in self.env:
            raise ValueError(self.env._(
                "'%(comodel_name)s' isn't a valid model name.",
                comodel_name=comodel_name,
            ))

        self.comodel_name = comodel_name
        self.domain = domain if domain is not None else Domain.TRUE

    @property
    def comodel_ids(self):
        if isinstance(self.domain, DynamicDomain):
            return None

        return self._get_comodel_ids(self.comodel_name, self.domain)

    def _next(self, known_vals):
        domain = self.domain(**known_vals) if isinstance(self.domain, DynamicDomain) else self.domain
        comodel_ids = self._get_comodel_ids(self.comodel_name, domain)

        if not comodel_ids:
            return False

        return self.distribution.choice(comodel_ids)

    @classmethod
    def convert_to_kwargs(cls, attrs):
        kwargs = super().convert_to_kwargs(attrs)

        if 'domain' in attrs:
            kwargs['domain'] = DynamicDomain(attrs['domain'])

        if 'comodel_name' in attrs:
            kwargs['comodel_name'] = attrs['comodel_name']

        return kwargs


class RelationMany(RelationOne):
    """
    Set a ``count`` +- ``std**2`` of random comodel records for X2many fields.

    If ``groupby`` is provided, the sampling is done per group.
    """
    name = 'relation.many'
    allowed_field_types = ('one2many', 'many2many', 'virtual')

    def __init__(self, count: int, std: int = 0, groupby: str | None = None, **kwargs):
        """Initialize sampling for X2many command values.

        :param count: Target number of related records to assign.
        :param std: Standard deviation used to vary ``count`` with a Gaussian draw.
        :param groupby: Optional comodel field; samples up to ``count`` records per group.
        """
        super().__init__(**kwargs)
        if self.unique:
            # It makes little sense to have a unique constraint on a X2many field
            raise ValueError(self.env._("Unique cannot be used with the '%s' generator.", self.name))

        assert count >= 0 and std >= 0
        self.count = count
        self.std = std

        if groupby is not None and groupby not in self.env[self.comodel_name]._fields:
            raise ValueError(self.env._(
                "'%(groupby)s' isn't a valid field for model '%(comodel_name)s'.",
                groupby=groupby,
                comodel_name=self.comodel_name,
            ))

        self.groupby = groupby

    def _next(self, known_vals):
        domain = self.domain(**known_vals) if isinstance(self.domain, DynamicDomain) else self.domain
        comodel_ids = self._get_comodel_ids(self.comodel_name, domain)

        if not comodel_ids or not self.count > 0:
            return False

        sample_count = (
            max(0, round(self.random.gauss(self.count, self.std)))
            if self.std
            else self.count
        )
        sampled_ids = []

        if self.groupby:
            records = self.env[self.comodel_name].browse(comodel_ids)
            for _, group in records.grouped(self.groupby).items():
                sample_count = clamp(sample_count, min_value=0, max_value=len(group))
                sampled_ids.extend(self.distribution.pick(group.ids, sample_count))
        else:
            # Make sure we have at least 1, e.g., a SO w/o SOL doesn't make sense.
            sample_count = clamp(sample_count, min_value=1, max_value=len(comodel_ids))
            sampled_ids = self.distribution.pick(comodel_ids, sample_count)

        return [Command.set(sampled_ids)]

    @classmethod
    def convert_to_kwargs(cls, attrs):
        kwargs = super().convert_to_kwargs(attrs)
        kwargs.update(**{k: int(v) for k, v in attrs.items() if k in ('count', 'std')})

        if 'groupby' in attrs:
            kwargs['groupby'] = attrs['groupby']

        return kwargs
