from __future__ import annotations

from ast import literal_eval
from typing import TYPE_CHECKING

from odoo.fields import Domain
from odoo.tools.safe_eval import expr_eval

from .expression import check_eval_kwargs, get_undefined_names

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from odoo.api import Environment, ValuesType
    from odoo.models import Model

    from ..models.blueprint import Blueprint
    from ..models.session import Session


class VirtualField:
    """
    Represents a field that exists only during data generation and is not persisted to the database.

    Virtual fields serve as intermediate computation steps in the data population pipeline.

    Virtual fields are particularly useful when you need to compute intermediate values
    that multiple real fields depend on, avoiding redundant calculations or complex
    lambda expressions.

    Example:
       In a blueprint definition, you might use a virtual 'markup' field to compute
       the actual 'cost' and 'price' fields:

       ```json
       {
           'price': {'generator': 'scalar.float', 'start': 1, 'end': 10},
           'markup': {'virtual': true, 'eval': '0.3'},
           'cost': {'virtual': true, 'eval': 'price / (1 + markup)'},
           'stock_quantity': {'eval': 'int(cost * 2)'}
       }
       ```

       Here, 'markup' and 'cost' are computed but not saved; only 'stock_quantity' is persisted.
    """

    def __init__(self, model_name: str, field_name: str):
        self.model_name = model_name
        self.name = field_name
        self.type = 'virtual'
        self.required = False
        self.comodel_name = None

    def __str__(self):
        return f"{self.model_name}.{self.name}"

    def __repr__(self):
        return f"VirtualField({self.model_name!r}, {self.name!r})"


class DynamicDomain:
    """
    Lazy domain resolver that evaluates expressions with references at runtime.

    Returns static ``Domain`` if no field references are found.
    Otherwise, returns a ``DynamicDomain`` instance that resolves the domain
    when called with field values.

    :param `domain_expr`: Domain string with optional field references,
        e.g., ``"[('company_id', '=', company_id)]"``.

    **Example**:

        >>> d = DynamicDomain("[('company_id', '=', company_id)]")
        >>> d(company_id=3)
        [('company_id', '=', 3)]
    """
    __slots__ = ('_resolver', 'dynamic_fields')
    dynamic_fields: list[str]
    _resolver: Callable[..., Domain]

    def __new__(cls, domain_expr: str) -> DynamicDomain | Domain:
        """Return a static domain or a dynamic resolver for ``domain_expr``.

        :param domain_expr: Domain expression from a blueprint attribute.
        :return: ``Domain`` when no field names are referenced, otherwise ``DynamicDomain``.
        """
        dynamic_fields = list(get_undefined_names(domain_expr))
        if not dynamic_fields:
            return Domain(literal_eval(domain_expr))

        self = super().__new__(cls)
        object.__setattr__(self, 'dynamic_fields', dynamic_fields)

        def checked(**eval_kwargs):
            check_eval_kwargs(eval_kwargs)
            return expr_eval(domain_expr, eval_kwargs)

        object.__setattr__(self, '_resolver', checked)
        return self

    def __call__(self, **depends: ValuesType) -> Domain:
        """Evaluate the dynamic domain with generated dependency values.

        :param depends: Generated values keyed by field name.
        :return: Domain with field references resolved to concrete values.
        """
        return Domain(self._resolver(**{
            field_name: depends[field_name]
            for field_name in self.dynamic_fields
        }))


def drop_pending_update(env: Environment, fnames: Iterable[str]):
    """Drop pending updates on dirty ``fnames`` for all models.

    :param env: Environment whose pending transaction updates should be pruned.
    :param fnames: Field names to clear from pending update tracking.
    """
    fnames = set(fnames)
    for field, ids in env.transaction.field_dirty.items():
        if field.name in fnames:
            ids.clear()

    # TODO(perf): can use the model from the field
    for model in env.values():
        model.invalidate_model(model._fields.keys() & fnames, flush=False)


def get_ref_domain(
    env: Environment,
    model_name: Model,
    ref: str,
    session: Session | None = None,
    blueprint: Blueprint | None = None,
) -> Domain:
    """Build a domain matching records created under a populate reference.

    Dot paths in ``ref`` are resolved from the referenced populated records, so
    ``"projects.task_ids"`` scopes the domain to tasks linked to populated projects.

    :param env: Environment used for searches.
    :param model_name: Target model the returned domain must match.
    :param ref: Populate reference, optionally followed by a dot path.
    :param session: Optional session scope.
    :param blueprint: Optional blueprint scope.
    :return: Domain matching the referenced records for ``model_name``.
    """
    scope_domain = Domain.TRUE

    if session:
        scope_domain &= Domain('session_id', '=', session.id)

    if blueprint:
        scope_domain &= Domain('blueprint_id', '=', blueprint.id)

    ref, _, path = ref.partition('.')
    if path:
        # Heuristic to find the ref's model_name
        # -> get from the first 'create' job with said ref.
        ref_job = env['populate.job'].search(
            scope_domain
            & Domain([
                ('type', '=', 'create'),
                ('parent_id', '=', False),
                ('ref', '=', ref),
            ]),
            limit=1,
        )
        ref_job.ensure_one()
        populated_records = env[ref_job.model_name].browse(
            env['populate.model.data'].search(
                scope_domain
                & Domain([
                    ('ref', '=', ref),
                    ('res_model', '=', ref_job.model_name),
                ]),
            ).mapped('res_id'),
        )
        populated_corecords = populated_records.mapped(path)
        if populated_corecords._name != model_name:
            raise ValueError(env._(
                "Field path '%(path)s' from '%(ref)s' resulted in model '%(got)s', "
                "but expected '%(expected)s'",
                path=path,
                ref=ref,
                got=populated_corecords._name,
                expected=model_name,
            ))
        domain = Domain('id', 'in', populated_corecords.ids)
    else:
        populated_records_ids = env['populate.model.data']._search(
            scope_domain
            & Domain([
                ('ref', '=', ref),
                ('res_model', '=', model_name),
            ]),
        ).select('res_id')
        domain = Domain('id', 'in', populated_records_ids)
    return domain
