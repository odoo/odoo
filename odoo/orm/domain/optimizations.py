"""Domain optimization functions.

This module contains all the optimization functions that are registered
to transform and simplify domain expressions.

The optimization system works in multiple levels:
- BASIC: Transaction-independent optimizations (type coercion, operator normalization)
- DYNAMIC_VALUES: Optimizations that may depend on dynamic values (relative dates)
- FULL: Complete optimizations including field search methods and record rules

Optimization functions are registered using decorators:
- @operator_optimization: Register optimization for specific operators
- @field_type_optimization: Register optimization for specific field types
- @nary_optimization: Register optimization for n-ary domain merging
- @nary_condition_optimization: Register optimization for condition merging
"""

import functools
import logging
import operator
import typing
import warnings
from collections.abc import Collection
from datetime import UTC, date, datetime, time, timedelta

from odoo.exceptions import MissingError
from odoo.libs.datetime import utc
from odoo.tools import SQL, OrderedSet, partition, str2bool
from odoo.tools.date_utils import parse_iso_date, resolve_date

from ..primitives import COLLECTION_TYPES
from .ast import (
    _FALSE_DOMAIN,
    _MERGE_OPTIMIZATIONS,
    _OPTIMIZATIONS_FOR,
    _TRUE_DOMAIN,
    ANY_TYPES,
    Domain,
    DomainAnd,
    DomainCondition,
    DomainNary,
    DomainOr,
    OptimizationLevel,
)
from .constants import (
    CONDITION_OPERATORS,
    INVERSE_OPERATOR,
    NEGATIVE_CONDITION_OPERATORS,
    STANDARD_CONDITION_OPERATORS,
)

if typing.TYPE_CHECKING:
    from ..models import BaseModel

_logger = logging.getLogger("odoo.domains")


# --------------------------------------------------
# Optimizations: registration decorators
# --------------------------------------------------


def operator_optimization(
    operators: Collection[str],
    level: OptimizationLevel = OptimizationLevel.BASIC,
):
    """Register a condition operator optimization for (condition, model)"""
    assert operators, "Missing operator to register"
    CONDITION_OPERATORS.update(operators)

    def register(optimization):
        mapping = _OPTIMIZATIONS_FOR[level]
        for op in operators:
            mapping[op].append(optimization)
        return optimization

    return register


def field_type_optimization(
    field_types: Collection[str],
    level: OptimizationLevel = OptimizationLevel.BASIC,
):
    """Register a condition optimization by field type for (condition, model)"""

    def register(optimization):
        mapping = _OPTIMIZATIONS_FOR[level]
        for field_type in field_types:
            mapping[field_type].append(optimization)
        return optimization

    return register


def nary_optimization(optimization):
    """Register an optimization to a list of children of an nary domain.

    The function will take an iterable containing optimized children of a
    n-ary domain and returns *optimized* domains.

    Note that you always need to optimize both AND and OR domains. It is always
    possible because if you can optimize `a & b` then you can optimize `a | b`
    because it is optimizing `~(~a & ~b)`. Since operators can be negated,
    all implementations of optimizations are implemented in a mirrored way:
    `(optimize AND) if some_condition == cls.ZERO.value else (optimize OR)`.

    The optimization of nary domains starts by optimizing the children,
    then sorts them by (field, operator_type, operator) where operator type
    groups similar operators together.
    """
    _MERGE_OPTIMIZATIONS.append(optimization)
    return optimization


def nary_condition_optimization(
    operators: Collection[str], field_types: Collection[str] | None = None
):
    """Register an optimization for condition children of an nary domain.

    The function will take a list of domain conditions of the same field and
    returns *optimized* domains.

    This is a adapter function that uses `nary_optimization`.

    NOTE: if you want to merge different operators, register for
    `operator=CONDITION_OPERATORS` and find conditions that you want to merge.
    """

    def register(optimization):
        @nary_optimization
        def optimizer(cls, domains: list[Domain], model):
            # find adjacent conditions with the same field and operators
            result = []
            merge_conditions: list[DomainCondition] = []
            for domain in domains:
                if isinstance(domain, DomainCondition) and domain.operator in operators:
                    field = domain._field(model)
                    if field_types is None or field.type in field_types:
                        if (
                            merge_conditions
                            and merge_conditions[0].field_expr == domain.field_expr
                        ):
                            merge_conditions.append(domain)
                            continue
                        # we are changing (field, operator), save the previous group
                        if len(merge_conditions) >= 2:
                            result.extend(optimization(cls, merge_conditions, model))
                        else:
                            result.extend(merge_conditions)
                        merge_conditions = [domain]
                        continue
                if merge_conditions:
                    if len(merge_conditions) >= 2:
                        result.extend(optimization(cls, merge_conditions, model))
                    else:
                        result.extend(merge_conditions)
                    merge_conditions = []
                result.append(domain)
            if merge_conditions:
                if len(merge_conditions) >= 2:
                    result.extend(optimization(cls, merge_conditions, model))
                else:
                    result.extend(merge_conditions)
            return result

        return optimization

    return register


# --------------------------------------------------
# Optimizations: conditions
# --------------------------------------------------


@operator_optimization(["=?"])
def _operator_equal_if_value(condition, _):
    """a =? b  <=>  not b or a = b"""
    if not condition.value:
        return _TRUE_DOMAIN
    return DomainCondition(condition.field_expr, "=", condition.value)


@operator_optimization(["<>"])
def _operator_different(condition, _):
    """a <> b  =>  a != b"""
    # already a rewrite-rule
    warnings.warn(
        "Operator '<>' is deprecated since 19.0, use '!=' directly",
        DeprecationWarning, stacklevel=2,
    )
    return DomainCondition(condition.field_expr, "!=", condition.value)


@operator_optimization(["=="])
def _operator_equals(condition, _):
    """a == b  =>  a = b"""
    # rewrite-rule
    warnings.warn(
        "Operator '==' is deprecated since 19.0, use '=' directly",
        DeprecationWarning, stacklevel=2,
    )
    return DomainCondition(condition.field_expr, "=", condition.value)


@operator_optimization(["=", "!="])
def _operator_equal_as_in(condition, _):
    """Equality operators.

    Validation for some types and translate collection into 'in'.
    """
    value = condition.value
    operator = "in" if condition.operator == "=" else "not in"
    if isinstance(value, COLLECTION_TYPES):
        # Equality against a collection (e.g., ('user_ids', '=', [])) is common
        # in views.  Kept at debug level because it's noisy and already handled
        # by silently converting to 'in'/'not in'.
        if (
            not value
        ):  # views sometimes use ('user_ids', '!=', []) to indicate the user is set
            _logger.debug(
                "The domain condition %r should compare with False.", condition
            )
            value = OrderedSet([False])
        else:
            _logger.debug(
                "The domain condition %r should use the 'in' or 'not in' operator.",
                condition,
            )
            value = OrderedSet(value)
    elif isinstance(value, SQL):
        # transform '=' SQL("x") into 'in' SQL("(x)")
        value = SQL("(%s)", value)
    else:
        value = OrderedSet((value,))
    return DomainCondition(condition.field_expr, operator, value)


@operator_optimization(["in", "not in"])
def _optimize_in_set(condition, _model):
    """Make sure the value is an OrderedSet or use 'any' operator"""
    value = condition.value
    if isinstance(value, OrderedSet) and value:
        # very common case, just skip creation of a new Domain instance
        return condition
    if isinstance(value, ANY_TYPES):
        operator = "any" if condition.operator == "in" else "not any"
        return DomainCondition(condition.field_expr, operator, value)
    if not value:
        return _FALSE_DOMAIN if condition.operator == "in" else _TRUE_DOMAIN
    if not isinstance(value, COLLECTION_TYPES):
        # Scalar value with 'in'/'not in' operator.  Common for group_ids,
        # user_ids fields — too noisy for a warning.  Silently wrap in list.
        _logger.debug("The domain condition %r should have a list value.", condition)
        value = [value]
    return DomainCondition(condition.field_expr, condition.operator, OrderedSet(value))


@operator_optimization(["in", "not in"])
def _optimize_in_required(condition, model):
    """Remove checks against a null value for required fields."""
    value = condition.value
    field = condition._field(model)
    if (
        field.falsy_value is None
        and (field.required or field.name == "id")
        and field in model.env.registry.not_null_fields
        # only optimize if there are no NewId's
        and all(model._ids)
    ):
        value = OrderedSet(v for v in value if v is not False)
    if len(value) == len(condition.value):
        return condition
    return DomainCondition(condition.field_expr, condition.operator, value)


@operator_optimization(["any", "not any", "any!", "not any!"])
def _optimize_any_domain(condition, model):
    """Make sure the value is an optimized domain (or Query or SQL)"""
    value = condition.value
    if isinstance(value, ANY_TYPES) and not isinstance(value, Domain):
        if condition.operator in ("any", "not any"):
            # update operator to 'any!'
            return DomainCondition(
                condition.field_expr, condition.operator + "!", condition.value
            )
        return condition
    domain = Domain(value)
    field = condition._field(model)
    if field.name == "id":
        # id ANY domain  <=>  domain
        # id NOT ANY domain  <=>  ~domain
        return domain if condition.operator in ("any", "any!") else ~domain
    if value is domain:
        # avoid recreating the same condition
        return condition
    return DomainCondition(condition.field_expr, condition.operator, domain)


# register and bind multiple levels later
def _optimize_any_domain_at_level(level: OptimizationLevel, condition, model):
    domain = condition.value
    if not isinstance(domain, Domain):
        return condition
    field = condition._field(model)
    if not field.relational:
        condition._raise("Cannot use 'any' with non-relational fields")
    try:
        comodel = model.env[field.comodel_name]
    except KeyError:
        condition._raise("Cannot determine the comodel relation")
    domain = domain._optimize(comodel, level)
    # const if the domain is empty, the result is a constant
    # if the domain is True, we keep it as is
    if domain.is_false():
        return _FALSE_DOMAIN if condition.operator in ("any", "any!") else _TRUE_DOMAIN
    if domain is condition.value:
        # avoid recreating the same condition
        return condition
    return DomainCondition(condition.field_expr, condition.operator, domain)


# Register for all optimization levels
for _level in OptimizationLevel:
    if _level > OptimizationLevel.NONE:
        operator_optimization(("any", "not any", "any!", "not any!"), _level)(
            functools.partial(_optimize_any_domain_at_level, _level)
        )
del _level


@operator_optimization([op for op in CONDITION_OPERATORS if op.endswith("like")])
def _optimize_like_str(condition, model):
    """Validate value for pattern matching, must be a str"""
    value = condition.value
    if not value:
        # =like matches only empty string (inverse the condition)
        result = (condition.operator in NEGATIVE_CONDITION_OPERATORS) == (
            "=" in condition.operator
        )
        # relational and non-relation fields behave differently
        if condition._field(model).relational or "=" in condition.operator:
            return DomainCondition(condition.field_expr, "!=" if result else "=", False)
        return Domain(result)
    if isinstance(value, str):
        return condition
    if isinstance(value, SQL):
        warnings.warn(
            "Since 19.0, use Domain.custom(to_sql=lambda model, alias, query: SQL(...))",
            DeprecationWarning, stacklevel=2,
        )
        return condition
    if "=" in condition.operator:
        condition._raise("The pattern to match must be a string", error=TypeError)
    return DomainCondition(condition.field_expr, condition.operator, str(value))


@field_type_optimization(["many2one", "one2many", "many2many"])
def _optimize_relational_name_search(condition, model):
    """Search relational using `display_name`.

    When a relational field is compared to a string, we actually want to make
    a condition on the `display_name` field.
    Negative conditions are translated into a "not any" for consistency.
    """
    operator = condition.operator
    value = condition.value
    positive_operator = NEGATIVE_CONDITION_OPERATORS.get(operator, operator)
    any_operator = "any" if positive_operator == operator else "not any"
    # Handle like operator
    if operator.endswith("like"):
        return DomainCondition(
            condition.field_expr,
            any_operator,
            DomainCondition("display_name", positive_operator, value),
        )
    # Handle inequality as not supported
    if operator[0] in ("<", ">") and isinstance(value, str):
        condition._raise(
            "Inequality not supported for relational field using a string",
            error=TypeError,
        )
    # Handle equality with str values
    if positive_operator != "in" or not isinstance(value, COLLECTION_TYPES):
        return condition
    str_values, other_values = partition(lambda v: isinstance(v, str), value)
    if not str_values:
        return condition
    domain = DomainCondition(
        condition.field_expr,
        any_operator,
        DomainCondition("display_name", positive_operator, str_values),
    )
    if other_values:
        if positive_operator == operator:
            domain |= DomainCondition(condition.field_expr, operator, other_values)
        else:
            domain &= DomainCondition(condition.field_expr, operator, other_values)
    return domain


@field_type_optimization(["boolean"])
def _optimize_boolean_in(condition, model):
    """b in boolean_values"""
    value = condition.value
    operator = condition.operator
    if operator not in ("in", "not in") or not isinstance(value, COLLECTION_TYPES):
        condition._raise(
            "Cannot compare %r to %s which is not a collection of length 1",
            condition.field_expr,
            type(value),
        )
    if not all(isinstance(v, bool) for v in value):
        # parse the values
        if any(isinstance(v, str) for v in value):
            # String-to-bool coercion happens during data import.  Kept at
            # debug level because import scenarios trigger this frequently.
            _logger.debug("Comparing boolean with a string in %s", condition)
        value = {
            str2bool(v.lower(), False) if isinstance(v, str) else bool(v) for v in value
        }
    if len(value) == 1 and not any(value):
        # when comparing boolean values, always compare to [True] if possible
        # it eases the implementation of search methods
        operator = INVERSE_OPERATOR[operator]
        value = [True]
    return DomainCondition(condition.field_expr, operator, value)


@field_type_optimization(["boolean"], OptimizationLevel.FULL)
def _optimize_boolean_in_all(condition, model):
    """b in [True, False]  =>  True"""
    if isinstance(condition.value, COLLECTION_TYPES) and set(condition.value) == {
        False,
        True,
    }:
        # tautology is simplified to a boolean
        # note that this optimization removes fields (like active) from the domain
        # so we do this only on FULL level to avoid removing it from sub-domains
        return Domain(condition.operator == "in")
    return condition


def _value_to_date(value, env, iso_only=False):
    # check datetime first, because it's a subclass of date
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date) or value is False:
        return value
    if isinstance(value, str):
        if iso_only:
            try:
                value = parse_iso_date(value)
            except ValueError:
                # check format
                resolve_date(value, env)
                return value
        else:
            value = resolve_date(value, env)
        return _value_to_date(value, env)
    if isinstance(value, COLLECTION_TYPES):
        return OrderedSet(_value_to_date(v, env=env, iso_only=iso_only) for v in value)
    if isinstance(value, SQL):
        warnings.warn(
            "Since 19.0, use Domain.custom(to_sql=lambda model, alias, query: SQL(...))",
            DeprecationWarning, stacklevel=2,
        )
        return value
    raise ValueError(f"Failed to cast {value!r} into a date")


@field_type_optimization(["date"])
def _optimize_type_date(condition, model):
    """Make sure we have a date type in the value"""
    operator = condition.operator
    if (
        operator not in ("in", "not in", ">", "<", "<=", ">=")
        or "." in condition.field_expr
    ):
        return condition
    value = _value_to_date(condition.value, model.env, iso_only=True)
    if value is False and operator[0] in ("<", ">"):
        # comparison to False results in an empty domain
        return _FALSE_DOMAIN
    return DomainCondition(condition.field_expr, operator, value)


@field_type_optimization(["date"], level=OptimizationLevel.DYNAMIC_VALUES)
def _optimize_type_date_relative(condition, model):
    operator = condition.operator
    if (
        operator not in ("in", "not in", ">", "<", "<=", ">=")
        or "." in condition.field_expr
        or not isinstance(condition.value, (str, OrderedSet))
    ):
        return condition
    value = _value_to_date(condition.value, model.env)
    return DomainCondition(condition.field_expr, operator, value)


def _value_to_datetime(value, env, iso_only=False):
    """Convert a value(s) to datetime.

    :returns: A tuple containing the converted value and a boolean indicating
              that all input values were dates.
              These are handled differently during rewrites.
    """
    if isinstance(value, datetime):
        if value.tzinfo:
            # Convert timezone-aware datetimes to naive UTC for storage
            value = value.astimezone(UTC).replace(tzinfo=None)
        return value, False
    if value is False:
        return False, True
    if isinstance(value, str):
        if iso_only:
            try:
                value = parse_iso_date(value)
            except ValueError:
                # check formatting
                _dt, is_date = _value_to_datetime(resolve_date(value, env), env)
                return value, is_date
        else:
            value = resolve_date(value, env)
        return _value_to_datetime(value, env)
    if isinstance(value, date):
        if value.year in (1, 9999):
            # avoid overflow errors, treat as UTC timezone
            tz = None
        elif (tz := env.tz) != utc:
            # get the tzinfo - attach timezone to naive datetime to get proper offset
            tz = datetime.combine(value, time.min).replace(tzinfo=tz).tzinfo
        else:
            tz = None
        value = datetime.combine(value, time.min, tz)
        if tz is not None:
            value = value.astimezone(UTC).replace(tzinfo=None)
        return value, True
    if isinstance(value, COLLECTION_TYPES):
        value, is_date = zip(
            *(_value_to_datetime(v, env=env, iso_only=iso_only) for v in value), strict=False
        )
        return OrderedSet(value), all(is_date)
    if isinstance(value, SQL):
        warnings.warn(
            "Since 19.0, use Domain.custom(to_sql=lambda model, alias, query: SQL(...))",
            DeprecationWarning, stacklevel=2,
        )
        return value, False
    raise ValueError(f"Failed to cast {value!r} into a datetime")


@field_type_optimization(["datetime"])
def _optimize_type_datetime(condition, model):
    """Make sure we have a datetime type in the value"""
    field_expr = condition.field_expr
    operator = condition.operator
    if operator not in ("in", "not in", ">", "<", "<=", ">=") or "." in field_expr:
        return condition
    value, is_date = _value_to_datetime(condition.value, model.env, iso_only=True)

    # Handle inequality
    if operator[0] in ("<", ">"):
        if value is False:
            return _FALSE_DOMAIN
        if not isinstance(value, datetime):
            return condition
        if value.microsecond:
            assert not is_date, "date don't have microseconds"
            value = value.replace(microsecond=0)
        delta = timedelta(days=1) if is_date else timedelta(seconds=1)
        if operator == ">":
            try:
                value += delta
            except OverflowError:
                # higher than max, not possible
                return _FALSE_DOMAIN
            operator = ">="
        elif operator == "<=":
            try:
                value += delta
            except OverflowError:
                # lower than max, just check if field is set
                return DomainCondition(field_expr, "!=", False)
            operator = "<"

    # Handle equality: compare to the whole second
    if (
        operator in ("in", "not in")
        and isinstance(value, COLLECTION_TYPES)
        and any(isinstance(v, datetime) for v in value)
    ):
        delta = timedelta(seconds=1)
        domain = DomainOr.apply(
            (
                DomainCondition(field_expr, ">=", v.replace(microsecond=0))
                & DomainCondition(field_expr, "<", v.replace(microsecond=0) + delta)
                if isinstance(v, datetime)
                else DomainCondition(field_expr, "=", v)
            )
            for v in value
        )
        if operator == "not in":
            domain = ~domain
        return domain

    return DomainCondition(field_expr, operator, value)


@field_type_optimization(["datetime"], level=OptimizationLevel.DYNAMIC_VALUES)
def _optimize_type_datetime_relative(condition, model):
    operator = condition.operator
    if (
        operator not in ("in", "not in", ">", "<", "<=", ">=")
        or "." in condition.field_expr
        or not isinstance(condition.value, (str, OrderedSet))
    ):
        return condition
    value, _ = _value_to_datetime(condition.value, model.env)
    return DomainCondition(condition.field_expr, operator, value)


@field_type_optimization(["binary"])
def _optimize_type_binary_attachment(condition, model):
    field = condition._field(model)
    operator = condition.operator
    value = condition.value
    if field.attachment and not (
        operator in ("in", "not in") and set(value) == {False}
    ):
        try:
            condition._raise(
                "Binary field stored in attachment, accepts only existence check; skipping domain"
            )
        except ValueError:
            # log with stacktrace
            _logger.exception("Invalid operator for a binary field")
        return _TRUE_DOMAIN
    if operator.endswith("like"):
        condition._raise(
            "Cannot use like operators with binary fields",
            error=NotImplementedError,
        )
    return condition


@operator_optimization(["parent_of", "child_of"], OptimizationLevel.FULL)
def _operator_hierarchy(condition, model):
    """Transform a hierarchy operator into a simpler domain.

    ### Semantic of hierarchical operator: `(field, operator, value)`

    `field` is either 'id' to indicate to use the default parent relation (`_parent_name`)
    or it is a field where the comodel is the same as the model.
    The value is used to search a set of `related_records`. We start from the given value,
    which can be ids, a name (for searching by name), etc. Then we follow up the relation;
    forward in case of `parent_of` and backward in case of `child_of`.
    The resulting domain will have 'id' if the field is 'id' or a many2one.

    In the case where the comodel is not the same as the model, the result is equivalent to
    `('field', 'any', ('id', operator, value))`
    """
    if condition.operator == "parent_of":
        hierarchy = _operator_parent_of_domain
    else:
        hierarchy = _operator_child_of_domain
    value = condition.value
    if value is False:
        return _FALSE_DOMAIN
    # Get:
    # - field: used in the resulting domain)
    # - parent (str | None): field name to find parent in the hierarchy
    # - comodel_sudo: used to resolve the hierarchy
    # - comodel: used to search for ids based on the value
    field = condition._field(model)
    if field.type == "many2one":
        comodel = model.env[field.comodel_name].with_context(active_test=False)
    elif field.type in ("one2many", "many2many"):
        comodel = model.env[field.comodel_name].with_context(**field.context)
    elif field.name == "id":
        comodel = model
    else:
        condition._raise(
            f"Cannot execute {condition.operator} for {field}, works only for relational fields"
        )
    comodel_sudo = comodel.sudo().with_context(active_test=False)
    parent = comodel._parent_name
    if comodel._name == model._name:
        if condition.field_expr != "id":
            parent = condition.field_expr
        if field.type == "many2one":
            field = model._fields["id"]
    # Get the initial ids and bind them to comodel_sudo before resolving the hierarchy
    if isinstance(value, (int, str)):
        value = [value]
    elif not isinstance(value, COLLECTION_TYPES):
        condition._raise(f"Value of type {type(value)} is not supported")
    coids, other_values = partition(lambda v: isinstance(v, int), value)
    search_domain = _FALSE_DOMAIN
    if field.type == "many2many":
        # always search for many2many
        search_domain |= DomainCondition("id", "in", coids)
        coids = []
    if other_values:
        # search for strings
        search_domain |= Domain.OR(
            Domain("display_name", "ilike", v) for v in other_values
        )
    coids += comodel.search(search_domain, order="id").ids
    if not coids:
        return _FALSE_DOMAIN
    result = hierarchy(comodel_sudo.browse(coids), parent)
    # Format the resulting domain
    if isinstance(result, Domain):
        if field.name == "id":
            return result
        return DomainCondition(field.name, "any!", result)
    return DomainCondition(field.name, "in", result)


def _operator_child_of_domain(comodel: BaseModel, parent):
    """Return a set of ids or a domain to find all children of given model"""
    if comodel._parent_store and parent == comodel._parent_name:
        try:
            paths = comodel.mapped("parent_path")
        except MissingError:
            paths = comodel.exists().mapped("parent_path")
        return Domain.OR(DomainCondition("parent_path", "=like", path + "%") for path in paths)  # type: ignore
    else:
        # recursively retrieve all children nodes with sudo(); the
        # filtering of forbidden records is done by the rest of the
        # domain
        child_ids: OrderedSet[int] = OrderedSet()
        while comodel:
            child_ids.update(comodel._ids)
            query = comodel._search(
                DomainCondition(parent, "in", OrderedSet(comodel.ids))
            )
            comodel = comodel.browse(OrderedSet(query.get_result_ids()) - child_ids)
    return child_ids


def _operator_parent_of_domain(comodel: BaseModel, parent):
    """Return a set of ids or a domain to find all parents of given model"""
    parent_ids: OrderedSet[int]
    if comodel._parent_store and parent == comodel._parent_name:
        try:
            paths = comodel.mapped("parent_path")
        except MissingError:
            paths = comodel.exists().mapped("parent_path")
        parent_ids = OrderedSet(
            int(label) for path in paths for label in path.split("/")[:-1]
        )
    else:
        # recursively retrieve all parent nodes with sudo() to avoid
        # access rights errors; the filtering of forbidden records is
        # done by the rest of the domain
        parent_ids = OrderedSet()
        try:
            comodel.mapped(parent)
        except MissingError:
            comodel = comodel.exists()
        while comodel:
            parent_ids.update(comodel._ids)
            comodel = comodel[parent].filtered(lambda p: p.id not in parent_ids)
    return parent_ids


@operator_optimization(["any", "not any"], level=OptimizationLevel.FULL)
def _optimize_any_with_rights(condition, model):
    if model.env.su or condition._field(model).bypass_search_access:
        return DomainCondition(
            condition.field_expr, condition.operator + "!", condition.value
        )
    return condition


@field_type_optimization(["many2one"], level=OptimizationLevel.FULL)
def _optimize_m2o_bypass_comodel_id_lookup(condition, model):
    """Avoid comodel's subquery, if it can be compared with the field directly"""
    operator = condition.operator
    if (
        operator in ("any!", "not any!")
        and isinstance(subdomain := condition.value, DomainCondition)
        and subdomain.field_expr == "id"
        and (suboperator := subdomain.operator) in ("in", "not in", "any!", "not any!")
    ):
        # We are bypassing permissions, we can transform:
        #  a ANY (id IN X)  =>  a IN (X - {False})
        #  a ANY (id NOT IN X)  =>  a NOT IN (X | {False})
        #  a ANY (id ANY X)  =>  a ANY X
        #  a ANY (id NOT ANY X)  =>  a != False AND a NOT ANY X
        #  a NOT ANY (id IN X)  =>  a NOT IN (X - {False})
        #  a NOT ANY (id NOT IN X)  =>  a IN (X | {False})
        #  a NOT ANY (id ANY X)  =>  a NOT ANY X
        #  a NOT ANY (id NOT ANY X)  =>  a = False OR a ANY X
        val = subdomain.value
        match suboperator:
            case "in":
                domain = DomainCondition(condition.field_expr, "in", val - {False})
            case "not in":
                domain = DomainCondition(condition.field_expr, "not in", val | {False})
            case "any!":
                domain = DomainCondition(condition.field_expr, "any!", val)
            case "not any!":
                domain = DomainCondition(
                    condition.field_expr, "!=", False
                ) & DomainCondition(condition.field_expr, "not any!", val)
        if operator == "not any!":
            domain = ~domain
        return domain

    return condition


# --------------------------------------------------
# Optimizations: nary
# --------------------------------------------------


def _merge_set_conditions(cls: type[DomainNary], conditions):
    """Base function to merge equality conditions.

    Combine the 'in' and 'not in' conditions to a single set of values.

    Examples:

        a in {1} or a in {2}  <=>  a in {1, 2}
        a in {1, 2} and a not in {2, 5}  =>  a in {1}
    """
    assert all(isinstance(cond.value, OrderedSet) for cond in conditions)

    # build the sets for 'in' and 'not in' conditions
    in_sets = [c.value for c in conditions if c.operator == "in"]
    not_in_sets = [c.value for c in conditions if c.operator == "not in"]

    # combine the sets
    field_expr = conditions[0].field_expr
    if cls.OPERATOR == "&":
        if in_sets:
            return [
                DomainCondition(
                    field_expr, "in", intersection(in_sets) - union(not_in_sets)
                )
            ]
        else:
            return [DomainCondition(field_expr, "not in", union(not_in_sets))]
    elif not_in_sets:
        return [
            DomainCondition(
                field_expr, "not in", intersection(not_in_sets) - union(in_sets)
            )
        ]
    else:
        return [DomainCondition(field_expr, "in", union(in_sets))]


def intersection(sets: list[OrderedSet]) -> OrderedSet:
    """Intersection of a list of OrderedSets."""
    return functools.reduce(operator.and_, sets)


def union(sets: list[OrderedSet]) -> OrderedSet:
    """Union of a list of OrderedSets"""
    return OrderedSet(elem for s in sets for elem in s)


@nary_condition_optimization(operators=("in", "not in"))
def _optimize_merge_set_conditions_mono_value(cls: type[DomainNary], conditions, model):
    """Merge equality conditions.

    Combine the 'in' and 'not in' conditions to a single set of values.
    Do not touch x2many fields which have a different semantic.

    Examples:

        a in {1} or a in {2}  <=>  a in {1, 2}
        a in {1, 2} and a not in {2, 5}  =>  a in {1}
    """
    field = conditions[0]._field(model)
    if field.type in ("many2many", "one2many", "properties"):
        return conditions
    return _merge_set_conditions(cls, conditions)


@nary_condition_optimization(operators=("in",), field_types=["many2many", "one2many"])
def _optimize_merge_set_conditions_x2many_in(cls: type[DomainNary], conditions, model):
    """Merge domains of 'in' conditions for x2many fields like for 'any' operator."""
    if cls is DomainAnd:
        return conditions
    return _merge_set_conditions(cls, conditions)


@nary_condition_optimization(
    operators=("not in",), field_types=["many2many", "one2many"]
)
def _optimize_merge_set_conditions_x2many_not_in(
    cls: type[DomainNary], conditions, model
):
    """Merge domains of 'not in' conditions for x2many fields like for 'not any' operator."""
    if cls is DomainOr:
        return conditions
    return _merge_set_conditions(cls, conditions)


@nary_condition_optimization(["any"], ["many2one", "one2many", "many2many"])
@nary_condition_optimization(["any!"], ["many2one", "one2many", "many2many"])
def _optimize_merge_any(cls, conditions, model):
    """Merge domains of 'any' conditions for relational fields.

    This will lead to a smaller number of sub-queries which are equivalent.
    Example:

        a any (f = 8) or a any (g = 5)  <=>  a any (f = 8 or g = 5)     (for all fields)
        a any (f = 8) and a any (g = 5)  <=>  a any (f = 8 and g = 5)   (for many2one fields only)
    """
    field = conditions[0]._field(model)
    if field.type != "many2one" and cls is DomainAnd:
        return conditions
    merge_conditions, other_conditions = partition(
        lambda c: isinstance(c.value, Domain), conditions
    )
    if len(merge_conditions) < 2:
        return conditions
    base = merge_conditions[0]
    sub_domain = cls(tuple(c.value for c in merge_conditions))
    return [
        DomainCondition(base.field_expr, base.operator, sub_domain),
        *other_conditions,
    ]


@nary_condition_optimization(["not any"], ["many2one", "one2many", "many2many"])
@nary_condition_optimization(["not any!"], ["many2one", "one2many", "many2many"])
def _optimize_merge_not_any(cls, conditions, model):
    """Merge domains of 'not any' conditions for relational fields.

    This will lead to a smaller number of sub-queries which are equivalent.
    Example:

        a not any (f = 1) or a not any (g = 5) => a not any (f = 1 and g = 5)   (for many2one fields only)
        a not any (f = 1) and a not any (g = 5) => a not any (f = 1 or g = 5)   (for all fields)
    """
    field = conditions[0]._field(model)
    if field.type != "many2one" and cls is DomainOr:
        return conditions
    merge_conditions, other_conditions = partition(
        lambda c: isinstance(c.value, Domain), conditions
    )
    if len(merge_conditions) < 2:
        return conditions
    base = merge_conditions[0]
    sub_domain = cls.INVERSE(tuple(c.value for c in merge_conditions))
    return [
        DomainCondition(base.field_expr, base.operator, sub_domain),
        *other_conditions,
    ]


@nary_optimization
def _optimize_same_conditions(cls, conditions, model):
    """Merge (adjacent) conditions that are the same.

    Quick optimization for some conditions, just compare if we have the same
    condition twice.
    """
    # check if we need to create a new list (this is usually not the case)
    prev = None
    for condition in conditions:
        if prev == condition:
            break
        prev = condition
    else:
        return conditions

    # avoid any function calls, and use the stack semantics for prev comparison
    prev = None
    return [condition for condition in conditions if prev != (prev := condition)]


__all__ = [
    "field_type_optimization",
    # Helper functions
    "intersection",
    "nary_condition_optimization",
    "nary_optimization",
    # Decorators
    "operator_optimization",
    "union",
]
