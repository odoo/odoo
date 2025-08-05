from __future__ import annotations

import typing
from collections import defaultdict

from odoo.tools.misc import SENTINEL, Sentinel, merge_sequences
from odoo.tools.sql import pg_varchar

from .fields import Field, _logger, determine, resolve_mro

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    from .types import BaseModel

    SelectValue = tuple[str, str]  # (value, string)
    OnDeletePolicy = str | Callable[[BaseModel], None]


class Selection(Field[str | typing.Literal[False]]):
    """ Encapsulates an exclusive choice between different values.

    :param selection: specifies the possible values for this field.
        It is given as either a list of pairs ``(value, label)``, or a model
        method, or a method name.
    :type selection: list(tuple(str,str)) or callable or str

    :param selection_add: provides an extension of the selection in the case
        of an overridden field. It is a list of pairs ``(value, label)`` or
        singletons ``(value,)``, where singleton values must appear in the
        overridden selection. The new values are inserted in an order that is
        consistent with the overridden selection and this list::

            selection = [('a', 'A'), ('b', 'B')]
            selection_add = [('c', 'C'), ('b',)]
            > result = [('a', 'A'), ('c', 'C'), ('b', 'B')]
    :type selection_add: list(tuple(str,str))

    :param ondelete: provides a fallback mechanism for any overridden
        field with a selection_add. It is a dict that maps every option
        from the selection_add to a fallback action.

        This fallback action will be applied to all records whose
        selection_add option maps to it.

        The actions can be any of the following:
            - 'set null' -- the default, all records with this option
              will have their selection value set to False.
            - 'cascade' -- all records with this option will be
              deleted along with the option itself.
            - 'set default' -- all records with this option will be
              set to the default of the field definition
            - 'set VALUE' -- all records with this option will be
              set to the given value
            - <callable> -- a callable whose first and only argument will be
              the set of records containing the specified Selection option,
              for custom processing

    The attribute ``selection`` is mandatory except in the case of
    ``related`` or extended fields.
    """
    type = 'selection'
    _column_type = ('varchar', pg_varchar())

    selection: list[SelectValue] | str | Callable[[BaseModel], list[SelectValue]] | None = None  # [(value, string), ...], function or method name
    validate: bool = True       # whether validating upon write
    ondelete: dict[str, OnDeletePolicy] | None = None  # {value: policy} (what to do when value is deleted)

    def __init__(self, selection=SENTINEL, string: str | Sentinel = SENTINEL, **kwargs):
        super().__init__(selection=selection, string=string, **kwargs)
        self._selection = dict(selection) if isinstance(selection, list) else None

    def setup_nonrelated(self, model):
        super().setup_nonrelated(model)
        assert self.selection is not None, "Field %s without selection" % self

    def setup_related(self, model):
        super().setup_related(model)
        # selection must be computed on related field
        field = self.related_field
        self.selection = lambda model: field._description_selection(model.env)
        self._selection = None

    def _get_attrs(self, model_class, name):
        attrs = super()._get_attrs(model_class, name)
        # arguments 'selection' and 'selection_add' are processed below
        attrs.pop('selection_add', None)
        # Selection fields have an optional default implementation of a group_expand function
        if attrs.get('group_expand') is True:
            attrs['group_expand'] = self._default_group_expand
        return attrs

    def _setup_attrs__(self, model_class, name):
        super()._setup_attrs__(model_class, name)
        if not self._base_fields:
            return

        # determine selection (applying 'selection_add' extensions) as a dict
        values = None

        for field in self._base_fields:
            # We cannot use field.selection or field.selection_add here
            # because those attributes are overridden by ``_setup_attrs__``.
            if 'selection' in field._args__:
                if self.related:
                    _logger.warning("%s: selection attribute will be ignored as the field is related", self)
                selection = field._args__['selection']
                if isinstance(selection, (list, tuple)):
                    if values is not None and list(values) != [kv[0] for kv in selection]:
                        _logger.warning("%s: selection=%r overrides existing selection; use selection_add instead", self, selection)
                    values = dict(selection)
                    self.ondelete = {}
                elif callable(selection) or isinstance(selection, str):
                    self.ondelete = None
                    self.selection = selection
                    values = None
                else:
                    raise ValueError(f"{self!r}: selection={selection!r} should be a list, a callable or a method name")

            if 'selection_add' in field._args__:
                if self.related:
                    _logger.warning("%s: selection_add attribute will be ignored as the field is related", self)
                selection_add = field._args__['selection_add']
                assert isinstance(selection_add, list), \
                    "%s: selection_add=%r must be a list" % (self, selection_add)
                assert values is not None, \
                    "%s: selection_add=%r on non-list selection %r" % (self, selection_add, self.selection)

                values_add = {kv[0]: (kv[1] if len(kv) > 1 else None) for kv in selection_add}
                ondelete = field._args__.get('ondelete') or {}
                new_values = [key for key in values_add if key not in values]
                for key in new_values:
                    ondelete.setdefault(key, 'set null')
                if self.required and new_values and 'set null' in ondelete.values():
                    raise ValueError(
                        "%r: required selection fields must define an ondelete policy that "
                        "implements the proper cleanup of the corresponding records upon "
                        "module uninstallation. Please use one or more of the following "
                        "policies: 'set default' (if the field has a default defined), 'cascade', "
                        "or a single-argument callable where the argument is the recordset "
                        "containing the specified option." % self
                    )

                # check ondelete values
                for key, val in ondelete.items():
                    if callable(val) or val in ('set null', 'cascade'):
                        continue
                    if val == 'set default':
                        assert self.default is not None, (
                            "%r: ondelete policy of type 'set default' is invalid for this field "
                            "as it does not define a default! Either define one in the base "
                            "field, or change the chosen ondelete policy" % self
                        )
                    elif val.startswith('set '):
                        assert val[4:] in values, (
                            "%s: ondelete policy of type 'set %%' must be either 'set null', "
                            "'set default', or 'set value' where value is a valid selection value."
                        ) % self
                    else:
                        raise ValueError(
                            "%r: ondelete policy %r for selection value %r is not a valid ondelete"
                            " policy, please choose one of 'set null', 'set default', "
                            "'set [value]', 'cascade' or a callable" % (self, val, key)
                        )

                values = {
                    key: values_add.get(key) or values[key]
                    for key in merge_sequences(values, values_add)
                }
                self.ondelete.update(ondelete)

        if values is not None:
            self.selection = list(values.items())
            assert all(isinstance(key, str) for key in values), \
                "Field %s with non-str value in selection" % self

        self._selection = values

    def _selection_modules(self, model):
        """ Return a mapping from selection values to modules defining each value. """
        if not isinstance(self.selection, list):
            return {}
        value_modules = defaultdict(set)
        for field in reversed(resolve_mro(model, self.name, type(self).__instancecheck__)):
            module = field._module
            if not module:
                continue
            if 'selection' in field._args__:
                value_modules.clear()
                if isinstance(field._args__['selection'], list):
                    for value, _label in field._args__['selection']:
                        value_modules[value].add(module)
            if 'selection_add' in field._args__:
                for value_label in field._args__['selection_add']:
                    if len(value_label) > 1:
                        value_modules[value_label[0]].add(module)
        return value_modules

    def _description_selection(self, env):
        """ return the selection list (pairs (value, label)); labels are
            translated according to context language
        """
        selection = self.selection
        if isinstance(selection, str) or callable(selection):
            selection = determine(selection, env[self.model_name])
            # force all values to be strings (check _get_year_selection)
            return [(str(key), str(label)) for key, label in selection]

        # translate selection labels
        if env.lang:
            return env['ir.model.fields'].get_field_selection(self.model_name, self.name)
        else:
            return selection

    def _default_group_expand(self, records, groups, domain):
        # return a group per selection option, in definition order
        return self.get_values(records.env)

    def get_values(self, env):
        """Return a list of the possible values."""
        selection = self.selection
        if isinstance(selection, str) or callable(selection):
            selection = determine(selection, env[self.model_name].with_context(lang=None))
        return [value for value, _ in selection]

    def convert_to_column(self, value, record, values=None, validate=True):
        if validate and self.validate:
            value = self.convert_to_cache(value, record)
        return super().convert_to_column(value, record, values, validate)

    def convert_to_cache(self, value, record, validate=True):
        if not validate or self._selection is None:
            return value or None
        if value in self._selection:
            return value
        if not value:
            return None
        raise ValueError("Wrong value for %s: %r" % (self, value))

    def convert_to_export(self, value, record):
        for item in self._description_selection(record.env):
            if item[0] == value:
                return item[1]
        return value or ''
