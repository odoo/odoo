from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from ast import literal_eval
from collections.abc import Mapping, Sequence
from functools import partial
from random import Random
from typing import TYPE_CHECKING, ClassVar, final

from odoo.fields import Domain
from odoo.tools import find_circular_dependency, frozendict, str2bool, topological_sort
from odoo.tools.lru import LRU

from ..utils.distributions import Distribution, UniformDistribution
from ..utils.orm import get_ref_domain
from odoo.addons.populate.utils.distributions import WeightedDistribution

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterable
    from typing import Any

    from odoo.api import DomainType, Environment, ValuesType
    from odoo.fields import Field

    from ..models.job import Job
    from ..models.session import Session
    from ..utils.orm import VirtualField

type DistributionFactory = Callable[[Random], Distribution]

MAX_RETRY = 10
DEFAULT_WEIGHT = 1
DEFAULT_GENERATORS = frozendict({
    'boolean': 'scalar.boolean',
    'integer': 'scalar.integer',
    'float': 'scalar.float',
    'monetary': 'scalar.monetary',
    'char': 'textual.char',
    'text': 'textual.text',
    'html': 'textual.text',
    'date': 'temporal.date',
    'datetime': 'temporal.datetime',
    'selection': 'choice.selection',
    'binary': 'binary.binary',
    'many2one': 'relation.one',
    'one2many': 'relation.many',
    'many2many': 'relation.many',
    'many2one_reference': 'reference.one',
    'reference': 'reference.raw',
    'properties': 'properties.value',
    'properties_definition': 'properties.definition',
})


class PopulateGeneratorError(Exception):
    """Base error for generator failures."""
    pass


class UnmetDependencies(PopulateGeneratorError):
    """Raised when required dependencies are missing."""
    pass


class UniqueValueNotFound(PopulateGeneratorError):
    """Raised when a unique value cannot be generated."""
    pass


class Generator(ABC):
    """
    Defines the base class `Generator` used to manage and generate values based on field
    attributes specified in a populate job.

    Concrete subclasses are registered in a global registry for retrieval.

    They must define a `name` class attribute and are responsible for implementing
    the `_next` method for value generation. `__init__` can be overridden to specify custom
    initialization parameters. If attributes from the field definition need to be converted into
    `__init__` arguments, override the `convert_to_kwargs` class method to handle the conversion.

    :ivar name: The unique name for the generator, used as its identifier in the registry
     and how it's referenced in blueprints.
    :ivar allowed_field_types: A tuple of allowed field types for this generator,
     or `None` for no restriction.
    """
    name: ClassVar[str]
    allowed_field_types: ClassVar[tuple[str] | None] = None
    _registry: ClassVar[dict[str, type[Generator]]] = {}

    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        if not inspect.isabstract(cls):
            if cls.name is None:
                raise TypeError(
                    f"Concrete Generator subclass '{cls.__qualname__}' "
                    f"must define a 'name' class attribute.",
                )

            Generator._registry[cls.name] = cls

    def _validate_field_type(self, field: Field | VirtualField):
        """Ensure this generator is compatible with the target field type.

        :param field: ORM field or virtual field targeted by the generator.
        :raise TypeError: If ``field.type`` is not allowed by the generator.
        """
        if self.allowed_field_types is not None and field.type not in self.allowed_field_types:
            raise TypeError(
                f"Incompatible field type '{field.type}'. "
                f"Expected field type(s): {self.allowed_field_types}.",
            )

    def __init__(
        self,
        field: Field | VirtualField,
        env: Environment,
        random: Random | None = None,
        job: Job | None = None,
        session: Session | None = None,
        valid_fields: Collection[str] | None = None,
        # Passed attributes
        values: Sequence[Any] | Mapping[Any, float] | None = None,
        depends: list[str] | None = None,
        null_ratio: float = 0,
        distribution: Distribution | DistributionFactory | None = None,
        unique: bool = False,
        **kwargs,
    ):
        """Initialize the common generation context and sampling options.

        :param field: ORM field or virtual field receiving generated values.
        :param env: Environment used for validation and database lookups.
        :param random: Random source shared across generators in the same job.
        :param job: Job that owns this generator, when available.
        :param session: Session scope used when a generator is created outside a job.
        :param valid_fields: Field names that dependency declarations may target.
        :param values: Explicit values, or values mapped to sampling weights.
        :param depends: Names of fields that must be generated before this one.
        :param null_ratio: Probability of returning ``False`` before sampling a value.
        :param distribution: Distribution instance or factory used for sampling.
        :param unique: Whether generated values must be unique for this job.
        """
        self._validate_field_type(field)

        self.field = field
        self.env = job.env if job else env

        if random is None:
            random = Random()

        self.random = random
        self.session = job.session_id if job else session
        self.job = job

        if valid_fields is None:
            if self.field.type == 'virtual':
                raise ValueError(self.env._(
                    "Cannot infer valid fields for a virtual field. "
                    "The 'valid_fields' parameter must be explicitly provided.",
                ))

            valid_fields = self.env[self.field.model_name]._fields.keys()

        if values is not None:
            if isinstance(values, Sequence):
                # A sequence is provided, then they have equal weights
                values = dict.fromkeys(values, DEFAULT_WEIGHT)

            elif isinstance(values, Mapping) and len(values.keys()) != len(set(values.keys())):
                # Having multiple instances of the same value will bias sampling
                raise ValueError(self.env._("Cannot have repeated entries in `values`."))

            self.weighted_values: Mapping[Any, float] = values
        else:
            self.weighted_values = {}

        if depends is None:
            depends = []

        if not all(dep in valid_fields for dep in depends):
            invalid_fields = [dep for dep in depends if dep not in valid_fields]
            raise ValueError(self.env._(
                "Invalid field dependencies: %(invalid_fields)s. "
                "These fields do not exist in the model's blueprint.",
                invalid_fields=invalid_fields,
            ))

        self.depends = depends

        if not (0 <= null_ratio <= 1):
            raise ValueError(self.env._(
                "Null fraction must be strictly between 0 and 1, got %(null_ratio)s instead.",
                null_ratio=null_ratio,
            ))

        if self.field.required and null_ratio:
            raise ValueError(self.env._(
                "Cannot specify a null fraction for a required field. "
                "Field '%(field_name)s' is required and cannot have null values.",
                field_name=self.field.name,
            ))

        if self.has_weights and null_ratio:
            # Don't allow null_ratio with weighted values as it would throw off the requested bias
            raise ValueError(self.env._(
                "Cannot specify a null fraction when using weighted values. "
                "The 'null_ratio' parameter is incompatible with custom weights.",
            ))

        self.null_ratio = null_ratio

        if distribution and self.has_weights:
            raise ValueError(self.env._(
                "Cannot have both a distribution and weighted values. "
                "Please provide either 'distribution' or 'values' with weights, but not both.",
            ))

        if self.has_weights:
            self.distribution = WeightedDistribution(
                weighted_values=self.weighted_values,
                random=self.random,
            )
        elif isinstance(distribution, Distribution):
            self.distribution = distribution
        elif callable(distribution):
            self.distribution = distribution(self.random)
        else:
            self.distribution = UniformDistribution(random=self.random)

        self.unique = unique
        self._init_seen()

    def _init_seen(self):
        """Initialize the value set used to enforce ``unique=True``."""
        if self.unique:
            if self.field.type == 'virtual':
                # Virtual fields are computed and not stored in the database.
                # Since we can't query existing values from the database,
                # we can only guarantee uniqueness within the current job run.
                # Therefore, values may be duplicated across different jobs and/or populate sessions.
                self._seen = set()
            else:
                model_name = self.field.model_name
                field_name = self.field.name
                present_values = (
                    self.env[model_name]
                    .search_fetch([], [field_name])
                    .mapped(field_name)
                )
                self._seen = {
                    seen_entry(value)
                    for value in present_values
                }
        else:
            self._seen = None

    def reset(self):
        """Reset uniqueness tracking so a dependency chain can be re-sampled."""
        self._seen = None
        self._init_seen()

    @property
    def values(self) -> list[Any]:
        return list(self.weighted_values.keys())

    @values.setter
    def values(self, new_values: Iterable):
        self.weighted_values = dict.fromkeys(new_values, DEFAULT_WEIGHT)

    @property
    def weights(self) -> list[float]:
        return list(self.weighted_values.values())

    @property
    def has_weights(self) -> bool:
        return not all(weight == DEFAULT_WEIGHT for weight in self.weighted_values.values())

    @final
    def next(self, known_vals: ValuesType) -> Any:
        """Generate the next value for this field based on known dependent field values.

        Subclasses should override ``_next`` for customization.

        :param known_vals: Values already generated for fields this generator can depend on.
        :return: Generated value, or ``False`` when selected by ``null_ratio``.
        :raise UnmetDependenciesError: If a required dependency is missing.
        :raise NoUniqueValueFoundError: If ``unique=True`` cannot be satisfied.
        """
        if not all(dep in known_vals for dep in self.depends):
            missing_deps = [dep for dep in self.depends if dep not in known_vals]
            raise UnmetDependencies(self.env._(
                "Could not generate a value because "
                "required dependencies are missing: %(missing_deps)s. "
                "Expected dependencies: %(expected_deps)s.",
                missing_deps=missing_deps,
                expected_deps=self.depends,
            ))

        if self.null_ratio and self.random.random() < self.null_ratio:
            return False

        if self.unique:
            for _ in range(MAX_RETRY):
                value = self._next(known_vals)
                entry = seen_entry(value)

                if entry in self._seen:
                    continue

                self._seen.add(entry)
                return value

            raise UniqueValueNotFound(self.env._(
                "Couldn't find a unique value for field %(field)s.",
                field=self.field,
            ))

        return self._next(known_vals)

    @abstractmethod
    def _next(self, known_vals: ValuesType) -> Any:
        """Internal implementation of Generator.next.

        To be overridden by subclasses.
        """
        ...

    @classmethod
    def convert_to_kwargs(cls, attrs: dict[str, str]) -> dict[str, Any]:
        """Convert the fields' attributes of job instructions into kwargs consumable by generators."""
        kwargs = {}

        if 'values' in attrs:
            kwargs['values'] = literal_eval(attrs['values'])

        if 'null_ratio' in attrs:
            kwargs['null_ratio'] = float(attrs['null_ratio'])

        if 'distribution' in attrs:
            distribution_def = attrs['distribution']
            distribution = Distribution.from_definition(distribution_def, partial=True)
            kwargs['distribution'] = distribution

        if 'unique' in attrs:
            value = attrs['unique']
            kwargs['unique'] = str2bool(value)

        if 'virtual' in attrs:
            # The field is of the type 'virtual', there is no need for an arg.
            attrs.pop('virtual')

        return kwargs

    @classmethod
    def by_name(cls, name: str) -> type[Generator]:
        """Return the generator class registered under ``name``.

        :param name: Blueprint generator name, such as ``scalar.integer``.
        :return: Matching generator class.
        """
        return cls._registry[name]


class ComodelGenerator(Generator):
    """
    Intermediate base for generators that resolve records from a comodel.

    Centralizes ref-scoping, caching, and partitioning of comodel IDs.
    """

    def __init__(self, ref: str | None = None, partition: bool = False, **kwargs):
        """Initialize common comodel lookup behavior.

        :param ref: Populate reference, optionally with a dot path, used to
            restrict candidate records.
        :param partition: Whether subjobs should split candidate records between
            sibling subjobs to reduce overlap during parallel execution.
        """
        super().__init__(**kwargs)

        self.ref = ref

        assert self.job or not partition

        if partition and self.job.parent_id:
            siblings_ids = self.job.parent_id.child_ids.ids
            self.subset = partial(
                round_robin_subset,
                count=len(siblings_ids),
                index=siblings_ids.index(self.job.id),
            )
        else:
            self.subset = None

        self._comodel_ids_cache = LRU(32)

    def _get_comodel_ids(self, comodel_name: str, domain: DomainType) -> list[int]:
        """Search, cache, and optionally partition candidate record ids.

        :param comodel_name: Model whose records are candidates.
        :param domain: Domain applied before ref scoping and partitioning.
        :return: Candidate record ids.
        """
        cache_key = (comodel_name, repr(domain))
        if cache_key in self._comodel_ids_cache:
            return self._comodel_ids_cache[cache_key]

        domain = Domain(domain)

        if self.ref:
            domain &= get_ref_domain(self.env, comodel_name, self.ref, self.session)

        ids = self.env[comodel_name].with_context(active_test=False).search(domain).ids

        if self.subset:
            ids = self.subset(ids)

        self._comodel_ids_cache[cache_key] = ids
        return ids

    @abstractmethod
    def _next(self, known_vals):
        ...

    @classmethod
    def convert_to_kwargs(cls, attrs):
        kwargs = super().convert_to_kwargs(attrs)

        if 'ref' in attrs:
            kwargs['ref'] = attrs['ref']

        if 'partition' in attrs:
            value = attrs['partition']
            kwargs['partition'] = str2bool(value)

        return kwargs


def get_fields_vals(generators: Mapping[str, Generator]) -> ValuesType:
    """Get the vals for a specific record that needs to be created/written.

    :param generators: Field generators keyed by field name.
    :return: Generated values suitable for ``create`` or ``write``.
    :raise GeneratorError: If generator dependencies contain a cycle.
    """
    vals = {}

    fields_depends = {
        field_name: generator.depends
        for field_name, generator in generators.items()
    }
    if cycle := find_circular_dependency(fields_depends):
        chain = ' -> '.join(str(n) for n in cycle)
        raise PopulateGeneratorError(
            f"Circular dependency detected in fields' generator dependencies: {chain}.",
        )

    for field_name in topological_sort(fields_depends):
        generator = generators[field_name]
        try:
            try:
                value = generator.next(vals)

            except UniqueValueNotFound:
                # A unique field couldn't find a novel value with the current
                # upstream values -> Re-roll the immediate dependencies if any.
                for _ in range(MAX_RETRY if generator.depends else 0):
                    for dep in generator.depends:
                        generators[dep].reset()
                        vals[dep] = generators[dep].next(vals)

                    try:
                        value = generator.next(vals)
                    except UniqueValueNotFound:
                        continue
                    else:
                        break
                else:
                    raise

        except Exception as exc:
            exc.add_note(f"Generator: '{generator.name}'")
            exc.add_note(f"Field: '{generator.field}'")
            raise

        vals[field_name] = value

    # Remove values from virtual fields.
    # Virtual fields may have the same name as real fields,
    # but we should not commit their values to the database.
    for field_name, generator in generators.items():
        if generator.field.type == 'virtual':
            vals.pop(field_name)

    return vals


def round_robin_subset[T](values: Sequence[T], count: int, index: int) -> list[T]:
    """Return one subset from a round-robin split of values.

    :param values: Sequence of values to distribute.
    :param count: Total number of subsets.
    :param index: Index of the subset to return, starting at 0.
    :return: Values assigned to ``index``.
    """
    return list(values[index::count])


def seen_entry(value):
    """Convert nested generated values into a hashable uniqueness key.

    :param value: Generated value to track for ``unique=True``.
    :return: Hashable representation of ``value``.
    """
    if isinstance(value, list):
        return tuple(seen_entry(v) for v in value)
    if isinstance(value, set):
        return frozenset(seen_entry(v) for v in value)
    if isinstance(value, dict):
        return tuple(sorted((k, seen_entry(v)) for k, v in value.items()))
    if isinstance(value, tuple):
        return tuple(seen_entry(v) for v in value)

    return value
