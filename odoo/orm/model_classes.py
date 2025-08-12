# Part of Odoo. See LICENSE file for full copyright and licensing details.

from __future__ import annotations

import logging
import typing

from collections import defaultdict

from . import models
from . import fields  # must be imported after models
from .utils import check_pg_name
from odoo.exceptions import ValidationError
from odoo.tools import (
    OrderedSet,
    LastOrderedSet,
    discardattr,
    frozendict,
    sql,
)

if typing.TYPE_CHECKING:
    from odoo.api import Environment
    from odoo.fields import Field
    from odoo.models import BaseModel
    from odoo.modules.registry import Registry

_logger = logging.getLogger('odoo.registry')

# THE MODEL DEFINITIONS, MODEL CLASSES, AND MODEL INSTANCES
#
# The framework deals with two kinds of classes for models: the "model
# definitions" and the "model classes".
#
# The "model definitions" are the classes defined in modules source code: they
# define models and extend them.  Those classes are essentially "static", for
# whatever that means in Python.  The only exception is custom models: their
# model definition is created dynamically.
#
# The "model classes" are the ones you find in the registry.  The recordsets of
# a model actually are instances of its model class.  The "model class" of a
# model is created dynamically when the registry is built.  It inherits (in the
# Python sense) from all the model definitions of the model, and possibly other
# model classes (when the model inherits from another model).  It also carries
# model metadata inferred from its parent classes.
#
#
# THE MODEL CLASSES
#
# In the simplest case, a model class inherits from all the classes that define
# the model in a flat hierarchy.  Consider the definitions of model 'a' below.
# The model class of 'a' inherits from the model definitions A1, A2, A3, in
# reverse order, to match the expected overriding order.  The model class
# carries inferred metadata that is shared between all the recordsets of that
# model for a given registry.
#
#       class A(Model):  # A1                 Model
#           _name = 'a'                       / | \
#                                            A3 A2 A1   <- model definitions
#       class A(Model):  # A2                 \ | /
#           _inherit = 'a'                      a       <- model class: registry['a']
#                                               |
#       class A(Model):  # A3                records    <- model instances, like env['a']
#           _inherit = 'a'
#
# Note that when the model inherits from another model, we actually make the
# model classes inherit from each other, so that extensions to an inherited
# model are visible in the model class of the child model, like in the
# following example.
#
#       class A(Model):  # A1
#           _name = 'a'                       Model
#                                            / / \ \
#       class B(Model):  # B1               / /   \ \
#           _name = 'b'                    / A2   A1 \
#                                         B2  \   /  B1
#       class B(Model):  # B2              \   \ /   /
#           _inherit = ['a', 'b']           \   a   /
#                                            \  |  /
#       class A(Model):  # A2                 \ | /
#           _inherit = 'a'                      b
#
# To be more explicit, the parent classes of model 'a' are (A2, A1), and the
# ones of model 'b' are (B2, a, B1).  Consequently, the MRO of model 'a' is
# [a, A2, A1, Model] while the MRO of 'b' is [b, B2, a, A2, A1, B1, Model].
#
#
# THE FIELDS OF A MODEL
#
# The fields of a model are given by the model's definitions, inherited models
# ('_inherit' and '_inherits') and other parties, like custom fields. Note that
# a field can be partially overridden when it appears on several definitions of
# its model.  In that case, the field's final definition depends on the
# presence or absence of each model definition, which itself depends on the
# modules loaded in the registry.
#
# By design, the model class has access to all the fields on its model
# definitions.  When possible, the field is used directly from its model
# definition.  There are a number of cases where the field cannot be used
# directly:
#  - the field is related (and bits may not be shared);
#  - the field is overridden on model definitions;
#  - the field is defined on another model (and accessible by mixin).
#
# The last case prevents sharing the field across registries, because the field
# object is specific to a model, and is used as a key in several key
# dictionaries, like the record cache and pending computations.
#
# Setting up a field on its model definition helps saving memory and time.
# Indeed, when sharing is possible, the field's setup is almost entirely done
# where the field was defined.  It is thus done when the model definition was
# created, and it may be reused across registries.
#
# In the example below, the field 'foo' appears once on its model definition.
# Assuming that it is not related, that field can be set up directly on its
# model definition.  If the model appears in several registries, the
# field 'foo' is effectively shared across registries.
#
#       class A1(Model):                      Model
#           _name = 'a'                        / \
#           foo = ...                         /   \
#           bar = ...                       A2     A1
#                                            bar    foo, bar
#       class A2(Model):                      \   /
#           _inherit = 'a'                     \ /
#           bar = ...                           a
#                                                bar
#
# On the other hand, the field 'bar' is overridden in its model definitions.  In
# that case, the framework recreates the field on the model class, which is
# never shared across registries.  The field's setup will be based on its
# definitions, and will thus not be shared across registries.
#
# The so-called magic fields ('id', 'display_name', ...) used to be added on
# model classes.  But doing so prevents them from being shared.  So instead,
# we add them on definition classes that define a model without extending it.
# This increases the number of fields that are shared across registries.


def is_model_definition(cls: type) -> bool:
    """ Return whether ``cls`` is a model definition class. """
    return isinstance(cls, models.MetaModel) and getattr(cls, 'pool', None) is None


def is_model_class(cls: type) -> bool:
    """ Return whether ``cls`` is a model registry class. """
    return getattr(cls, 'pool', None) is not None


def add_to_registry(registry: Registry, model_def: type[BaseModel]) -> type[BaseModel]:
    """ Add a model definition to the given registry, and return its
    corresponding model class.  This function creates or extends a model class
    for the given model definition.
    """
    assert is_model_definition(model_def)

    if hasattr(model_def, '_constraints'):
        _logger.warning("Model attribute '_constraints' is no longer supported, "
                        "please use @api.constrains on methods instead.")
    if hasattr(model_def, '_sql_constraints'):
        _logger.warning("Model attribute '_sql_constraints' is no longer supported, "
                        "please define model.Constraint on the model.")

    # all models except 'base' implicitly inherit from 'base'
    name = model_def._name
    parent_names = list(model_def._inherit)
    if name != 'base':
        parent_names.append('base')

    # create or retrieve the model's class
    if name in parent_names:
        if name not in registry:
            raise TypeError(f"Model {name!r} does not exist in registry.")
        model_cls = registry[name]
        _check_model_extension(model_cls, model_def)
    else:
        model_cls = type(name, (model_def,), {
            'pool': registry,                       # this makes it a model class
            '_name': name,
            '_register': False,
            '_original_module': model_def._module,
            '_inherit_module': {},                  # map parent to introducing module
            '_inherit_children': OrderedSet(),      # names of children models
            '_inherits_children': set(),            # names of children models
            '_fields': {},                          # populated in _setup()
            '_table_objects': frozendict(),         # populated in _setup()
        })

    # determine all the classes the model should inherit from
    bases = LastOrderedSet([model_def])
    for parent_name in parent_names:
        if parent_name not in registry:
            raise TypeError(f"Model {name!r} inherits from non-existing model {parent_name!r}.")
        parent_cls = registry[parent_name]
        if parent_name == name:
            for base in parent_cls._base_classes__:
                bases.add(base)
        else:
            _check_model_parent_extension(model_cls, model_def, parent_cls)
            bases.add(parent_cls)
            model_cls._inherit_module[parent_name] = model_def._module
            parent_cls._inherit_children.add(name)

    # model_cls.__bases__ must be assigned those classes; however, this
    # operation is quite slow, so we do it once in method _prepare_setup()
    model_cls._base_classes__ = tuple(bases)

    # determine the attributes of the model's class
    _init_model_class_attributes(model_cls)

    check_pg_name(model_cls._table)

    # Transience
    if model_cls._transient and not model_cls._log_access:
        raise TypeError(
            "TransientModels must have log_access turned on, "
            "in order to implement their vacuum policy"
        )

    # update the registry after all checks have passed
    registry[name] = model_cls

    return model_cls


def _check_model_extension(model_cls: type[BaseModel], model_def: type[BaseModel]):
    """ Check whether ``model_cls`` can be extended with ``model_def``. """
    if model_cls._abstract and not model_def._abstract:
        raise TypeError(
            f"{model_def} transforms the abstract model {model_cls._name!r} into a non-abstract model. "
            "That class should either inherit from AbstractModel, or set a different '_name'."
        )
    if model_cls._transient != model_def._transient:
        if model_cls._transient:
            raise TypeError(
                f"{model_def} transforms the transient model {model_cls._name!r} into a non-transient model. "
                "That class should either inherit from TransientModel, or set a different '_name'."
            )
        else:
            raise TypeError(
                f"{model_def} transforms the model {model_cls._name!r} into a transient model. "
                "That class should either inherit from Model, or set a different '_name'."
            )


def _check_model_parent_extension(model_cls: type[BaseModel], model_def: type[BaseModel], parent_cls: type[BaseModel]):
    """ Check whether ``model_cls`` can inherit from ``parent_cls``. """
    if model_cls._abstract and not parent_cls._abstract:
        raise TypeError(
            f"In {model_def}, abstract model {model_cls._name!r} cannot inherit from non-abstract model {parent_cls._name!r}."
        )


def _init_model_class_attributes(model_cls: type[BaseModel]):
    """ Initialize model class attributes. """
    assert is_model_class(model_cls)

    model_cls._description = model_cls._name
    model_cls._table = model_cls._name.replace('.', '_')
    model_cls._log_access = model_cls._auto
    inherits = {}
    depends = {}

    for base in reversed(model_cls._base_classes__):
        if is_model_definition(base):
            # the following attributes are not taken from registry classes
            if model_cls._name not in base._inherit and not base._description:
                _logger.warning("The model %s has no _description", model_cls._name)
            model_cls._description = base._description or model_cls._description
            model_cls._table = base._table or model_cls._table
            model_cls._log_access = getattr(base, '_log_access', model_cls._log_access)

        inherits.update(base._inherits)

        for mname, fnames in base._depends.items():
            depends.setdefault(mname, []).extend(fnames)

    # avoid assigning an empty dict to save memory
    if inherits:
        model_cls._inherits = inherits
    if depends:
        model_cls._depends = depends

    # update _inherits_children of parent models
    registry = model_cls.pool
    for parent_name in model_cls._inherits:
        registry[parent_name]._inherits_children.add(model_cls._name)

    # recompute attributes of _inherit_children models
    for child_name in model_cls._inherit_children:
        _init_model_class_attributes(registry[child_name])


def setup_model_classes(env: Environment):
    registry = env.registry

    # we must setup ir.model before adding manual fields because _add_manual_models may
    # depend on behavior that is implemented through overrides, such as is_mail_thread which
    # is implemented through an override to env['ir.model']._instanciate_attrs
    _prepare_setup(env['ir.model'])

    # add manual models
    if registry._init_modules:
        _add_manual_models(env)

    # prepare the setup on all models
    models = list(env.values())
    for model in models:
        _prepare_setup(model)

    # do the actual setup
    for model in models:
        _setup(model)

    registry._m2m: defaultdict[tuple[str, str, str], list[Field]] = defaultdict(list)
    for model in models:
        _setup_fields(model)
    del registry._m2m

    for model in models:
        model._post_model_setup__()


def _prepare_setup(model: BaseModel):
    """ Prepare the setup of the model. """
    model_cls = model.env.registry[model._name]
    model_cls._setup_done__ = False

    # changing base classes is costly, do it only when necessary
    if model_cls.__bases__ != model_cls._base_classes__:
        model_cls.__bases__ = model_cls._base_classes__

    # reset those attributes on the model's class for _setup_fields() below
    for attr in ('_rec_name', '_active_name'):
        discardattr(model_cls, attr)

    # reset properties memoized on model_cls
    model_cls._constraint_methods = models.BaseModel._constraint_methods
    model_cls._ondelete_methods = models.BaseModel._ondelete_methods
    model_cls._onchange_methods = models.BaseModel._onchange_methods


def _setup(model: BaseModel):
    """ Determine all the fields of the model. """
    model_cls = model.env.registry[model._name]
    if model_cls._setup_done__:
        return

    # the classes that define this model, i.e., the ones that are not
    # registry classes; the purpose of this attribute is to behave as a
    # cache of [c for c in model_cls.mro() if not is_model_class(c))], which
    # is heavily used in function fields.resolve_mro()
    model_cls._model_classes__ = tuple(c for c in model_cls.mro() if getattr(c, 'pool', None) is None)

    # 1. determine the proper fields of the model: the fields defined on the
    # class and magic fields, not the inherited or custom ones

    # retrieve fields from parent classes, and duplicate them on model_cls to
    # avoid clashes with inheritance between different models
    for name in model_cls._fields:
        discardattr(model_cls, name)
    model_cls._fields.clear()

    # collect the definitions of each field (base definition + overrides)
    definitions = defaultdict(list)
    for cls in reversed(model_cls._model_classes__):
        # this condition is an optimization of is_model_definition(cls)
        if isinstance(cls, models.MetaModel):
            for field in cls._field_definitions:
                definitions[field.name].append(field)

    for name, fields_ in definitions.items():
        if f'{model_cls._name}.{name}' in model_cls.pool._database_translated_fields:
            # the field is currently translated in the database; ensure the
            # field is translated to avoid converting its column to varchar
            # and losing data
            translate = next((
                field._args__['translate'] for field in reversed(fields_) if 'translate' in field._args__
            ), False)
            if not translate:
                # patch the field definition by adding an override
                _logger.debug("Patching %s.%s with translate=True", model_cls._name, name)
                fields_.append(type(fields_[0])(translate=True))
        if f'{model_cls._name}.{name}' in model_cls.pool._database_company_dependent_fields:
            # the field is currently company dependent in the database; ensure
            # the field is company dependent to avoid converting its column to
            # the base data type
            company_dependent = next((
                field._args__['company_dependent'] for field in reversed(fields_) if 'company_dependent' in field._args__
            ), False)
            if not company_dependent:
                # validate column type again in case the column type is changed by upgrade script
                rows = model.env.execute_query(sql.SQL(
                    'SELECT data_type FROM information_schema.columns WHERE table_name = %s AND column_name = %s',
                    model_cls._table, name
                ))
                if rows and rows[0][0] == 'jsonb':
                    # patch the field definition by adding an override
                    _logger.warning("Patching %s.%s with company_dependent=True", model_cls._name, name)
                    fields_.append(type(fields_[0])(company_dependent=True))
        if len(fields_) == 1 and fields_[0]._direct and fields_[0].model_name == model_cls._name:
            model_cls._fields[name] = fields_[0]
        else:
            Field = type(fields_[-1])
            add_field(model, name, Field(_base_fields=tuple(fields_)))

    # 2. add manual fields
    if model.pool._init_modules:
        _add_manual_fields(model)

    # 3. make sure that parent models determine their own fields, then add
    # inherited fields to model_cls
    _check_inherits(model)
    for parent_name in model._inherits:
        _setup(model.env[parent_name])
    _add_inherited_fields(model)

    # 4. initialize more field metadata
    model_cls._setup_done__ = True

    for field in model_cls._fields.values():
        field.prepare_setup()

    # 5. determine and validate rec_name
    if model_cls._rec_name:
        assert model_cls._rec_name in model_cls._fields, \
            "Invalid _rec_name=%r for model %r" % (model_cls._rec_name, model_cls._name)
    elif 'name' in model_cls._fields:
        model_cls._rec_name = 'name'
    elif model_cls._custom and 'x_name' in model_cls._fields:
        model_cls._rec_name = 'x_name'

    # 6. determine and validate active_name
    if model_cls._active_name:
        assert (model_cls._active_name in model_cls._fields
                and model_cls._active_name in ('active', 'x_active')), \
            ("Invalid _active_name=%r for model %r; only 'active' and "
            "'x_active' are supported and the field must be present on "
            "the model") % (model_cls._active_name, model_cls._name)
    elif 'active' in model_cls._fields:
        model_cls._active_name = 'active'
    elif 'x_active' in model_cls._fields:
        model_cls._active_name = 'x_active'

    # 7. determine table objects
    assert not model_cls._table_object_definitions, "model_cls is a registry model"
    model_cls._table_objects = frozendict({
        cons.full_name(model): cons
        for cls in reversed(model_cls._model_classes__)
        if isinstance(cls, models.MetaModel)
        for cons in cls._table_object_definitions
    })


def _check_inherits(model: BaseModel):
    for comodel_name, field_name in model._inherits.items():
        field = model._fields.get(field_name)
        if not field or field.type != 'many2one':
            raise TypeError(
                f"Missing many2one field definition for _inherits reference {field_name!r} in model {model._name!r}. "
                f"Add a field like: {field_name} = fields.Many2one({comodel_name!r}, required=True, ondelete='cascade')"
            )
        if not (field.delegate and field.required and (field.ondelete or "").lower() in ("cascade", "restrict")):
            raise TypeError(
                f"Field definition for _inherits reference {field_name!r} in {model._name!r} "
                "must be marked as 'delegate', 'required' with ondelete='cascade' or 'restrict'"
            )


def _add_inherited_fields(model: BaseModel):
    """ Determine inherited fields. """
    if model._abstract or not model._inherits:
        return

    # determine which fields can be inherited
    to_inherit = {
        name: (parent_fname, field)
        for parent_model_name, parent_fname in model._inherits.items()
        for name, field in model.env[parent_model_name]._fields.items()
    }

    # add inherited fields that are not redefined locally
    for name, (parent_fname, field) in to_inherit.items():
        if name not in model._fields:
            # inherited fields are implemented as related fields, with the
            # following specific properties:
            #  - reading inherited fields should not bypass access rights
            #  - copy inherited fields iff their original field is copied
            field_cls = type(field)
            add_field(model, name, field_cls(
                inherited=True,
                inherited_field=field,
                related=f"{parent_fname}.{name}",
                related_sudo=False,
                copy=field.copy,
                readonly=field.readonly,
                export_string_translation=field.export_string_translation,
            ))


def _setup_fields(model: BaseModel):
    """ Setup the fields, except for recomputation triggers. """
    bad_fields = []
    many2one_company_dependents = model.env.registry.many2one_company_dependents
    for name, field in model._fields.items():
        try:
            field.setup(model)
        except Exception:
            if field.base_field.manual:
                # Something goes wrong when setup a manual field.
                # This can happen with related fields using another manual many2one field
                # that hasn't been loaded because the comodel does not exist yet.
                # This can also be a manual function field depending on not loaded fields yet.
                bad_fields.append(name)
                continue
            raise
        if field.type == 'many2one' and field.company_dependent:
            many2one_company_dependents.add(field.comodel_name, field)

    for name in bad_fields:
        pop_field(model, name)


def _add_manual_models(env: Environment):
    """ Add extra models to the registry. """
    # clean up registry first
    for name, model_cls in list(env.registry.items()):
        if model_cls._custom:
            del env.registry.models[name]
            # remove the model's name from its parents' _inherit_children
            for parent_cls in model_cls.__bases__:
                if hasattr(parent_cls, 'pool'):
                    parent_cls._inherit_children.discard(name)

    # we cannot use self._fields to determine translated fields, as it has not been set up yet
    env.cr.execute("SELECT *, name->>'en_US' AS name FROM ir_model WHERE state = 'manual'")
    for model_data in env.cr.dictfetchall():
        attrs = env['ir.model']._instanciate_attrs(model_data)

        # adapt _auto and _log_access if necessary
        table_name = model_data["model"].replace(".", "_")
        table_kind = sql.table_kind(env.cr, table_name)
        if table_kind not in (sql.TableKind.Regular, None):
            _logger.info(
                "Model %r is backed by table %r which is not a regular table (%r), disabling automatic schema management",
                model_data["model"], table_name, table_kind,
            )
            attrs['_auto'] = False
            env.cr.execute(
                """ SELECT a.attname
                    FROM pg_attribute a
                    JOIN pg_class t ON a.attrelid = t.oid AND t.relname = %s
                    WHERE a.attnum > 0 -- skip system columns """,
                [table_name]
            )
            columns = {colinfo[0] for colinfo in env.cr.fetchall()}
            attrs['_log_access'] = set(models.LOG_ACCESS_COLUMNS) <= columns

        model_def = type('CustomDefinitionModel', (models.Model,), attrs)
        add_to_registry(env.registry, model_def)


def _add_manual_fields(model: BaseModel):
    """ Add extra fields on model. """
    IrModelFields = model.env['ir.model.fields']

    fields_data = IrModelFields._get_manual_field_data(model._name)
    for name, field_data in fields_data.items():
        if name not in model._fields and field_data['state'] == 'manual':
            try:
                attrs = IrModelFields._instanciate_attrs(field_data)
                if attrs:
                    field = fields.Field.by_type[field_data['ttype']](**attrs)
                    add_field(model, name, field)
            except Exception:
                _logger.exception("Failed to load field %s.%s: skipped", model._name, field_data['name'])


def add_field(model: BaseModel, name: str, field: Field):
    """ Add the given ``field`` under the given ``name`` on the model class of the given ``model``. """
    model_cls = model.env.registry[model._name]

    # Assert the name is an existing field in the model, or any model in the _inherits
    # or a custom field (starting by `x_`)
    is_class_field = any(
        isinstance(getattr(model, name, None), fields.Field)
        for model in [model_cls] + [model.env.registry[inherit] for inherit in model_cls._inherits]
    )
    if not (is_class_field or model.env['ir.model.fields']._is_manual_name(name)):
        raise ValidationError(  # pylint: disable=missing-gettext
            f"The field `{name}` is not defined in the `{model_cls._name}` Python class and does not start with 'x_'"
        )

    # Assert the attribute to assign is a Field
    if not isinstance(field, fields.Field):
        raise ValidationError("You can only add `fields.Field` objects to a model fields")  # pylint: disable=missing-gettext

    if not isinstance(getattr(model_cls, name, field), fields.Field):
        _logger.warning("In model %r, field %r overriding existing value", model_cls._name, name)
    setattr(model_cls, name, field)
    field._toplevel = True
    field.__set_name__(model_cls, name)
    # add field as an attribute and in model_cls._fields (for reflection)
    model_cls._fields[name] = field


def pop_field(model: BaseModel, name: str) -> Field | None:
    """ Remove the field with the given ``name`` from the model class of ``model``. """
    model_cls = model.env.registry[model._name]
    field = model_cls._fields.pop(name, None)
    discardattr(model_cls, name)
    if model_cls._rec_name == name:
        # fixup _rec_name and display_name's dependencies
        model_cls._rec_name = None
        if model_cls.display_name in model_cls.pool.field_depends:
            model_cls.pool.field_depends[model_cls.display_name] = tuple(
                dep for dep in model_cls.pool.field_depends[model_cls.display_name] if dep != name
            )
    return field
