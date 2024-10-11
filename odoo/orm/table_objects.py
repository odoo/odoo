from __future__ import annotations

import typing

from odoo.tools import sql

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    import psycopg2.extensions

    from .environments import Environment
    from .models import BaseModel

    ConstraintMessageType = (
        str
        | Callable[[Environment, psycopg2.extensions.Diagnostics | None], str]
    )


class TableObject:
    """ Declares a SQL object related to the model.

    The identifier of the SQL object will be "{model._table}_{name}".
    """
    name: str
    message: ConstraintMessageType = ''
    _module: str = ''

    def __init__(self):
        """Abstract SQL object"""
        # to avoid confusion: name is unique inside the model, full_name is in the database
        self.name = ''

    def __set_name__(self, owner, name):
        # database objects should be private member fo the class:
        # first of all, you should not need to access them from any model
        # and this avoid having them in the middle of the fields when listing members
        assert name.startswith('_'), "Names of SQL objects in a model must start with '_'"
        self.name = name[1:]
        if getattr(owner, 'pool', None) is None:  # models.is_definition_class(owner)
            # only for fields on definition classes, not registry classes
            self._module = owner._module
            owner._table_object_definitions.append(self)

    @property
    def definition(self) -> str:
        raise NotImplementedError

    def full_name(self, model: BaseModel) -> str:
        assert self.name, f"The table object is not named ({self.definition})"
        name = f"{model._table}_{self.name}"
        return sql.make_identifier(name)

    def get_error_message(self, model: BaseModel, diagnostics=None) -> str:
        """Build an error message for the object/constraint.

        :param model: Optional model on which the constraint is defined
        :param diagnostics: Optional diagnostics from the raised exception
        :return: Translated error for the user
        """
        message = self.message
        if callable(message):
            return message(model.env, diagnostics)
        return message

    def apply_to_database(self, model: BaseModel):
        raise NotImplementedError

    def __str__(self) -> str:
        return f"({self.name!r}={self.definition!r}, {self.message!r})"


class Constraint(TableObject):
    """ SQL table constraint.

    The definition of the constraint is used to `ADD CONSTRAINT` on the table.
    """

    def __init__(
        self,
        definition: str,
        message: ConstraintMessageType = '',
    ) -> None:
        """ SQL table containt.

        The definition is the SQL that will be used to add the constraint.
        If the constraint is violated, we will show the message to the user
        or an empty string to get a default message.

        Examples of constraint definitions:
        - CHECK (x > 0)
        - FOREIGN KEY (abc) REFERENCES some_table(id)
        - UNIQUE (user_id)
        """
        super().__init__()
        self._definition = definition
        if message:
            self.message = message

    @property
    def definition(self):
        return self._definition

    def apply_to_database(self, model: BaseModel):
        cr = model.env.cr
        conname = self.full_name(model)
        definition = self.definition
        current_definition = sql.constraint_definition(cr, model._table, conname)
        if current_definition == definition:
            return

        if current_definition:
            # constraint exists but its definition may have changed
            sql.drop_constraint(cr, model._table, conname)

        if not definition:
            # virtual constraint (e.g. implemented by a custom index)
            model.pool.post_init(sql.check_index_exist, cr, conname)
        model.pool.post_constraint(sql.add_constraint, cr, model._table, conname, definition)
