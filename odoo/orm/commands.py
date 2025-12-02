from __future__ import annotations

import enum
import typing

if typing.TYPE_CHECKING:
    from collections.abc import Collection
    from .types import ValuesType


class Command(enum.IntEnum):
    """
    :class:`~odoo.fields.One2many` and :class:`~odoo.fields.Many2many` fields
    expect a special command to manipulate the relation they implement.

    Internally, each command is a 3-elements tuple where the first element is a
    mandatory integer that identifies the command, the second element is either
    the related record id to apply the command on (commands update, delete,
    unlink and link) either 0 (commands create, clear and set), the third
    element is either the ``values`` to write on the record (commands create
    and update) either the new ``ids`` list of related records (command set),
    either 0 (commands delete, unlink, link, and clear).
    This triplet is aliased as ``CommandValue``.

    Via Python, we encourage developers craft new commands via the various
    functions of this namespace. We also encourage developers to use the
    command identifier constant names when comparing the 1st element of
    existing commands.

    Via RPC, it is impossible nor to use the functions nor the command constant
    names. It is required to instead write the literal 3-elements tuple where
    the first element is the integer identifier of the command.
    """

    CREATE = 0
    UPDATE = 1
    DELETE = 2
    UNLINK = 3
    LINK = 4
    CLEAR = 5
    SET = 6

    @classmethod
    def create(cls, values: ValuesType) -> CommandValue:
        """
        Create new records in the comodel using ``values``, link the created
        records to ``self``.

        In case of a :class:`~odoo.fields.Many2many` relation, one unique
        new record is created in the comodel such that all records in `self`
        are linked to the new record.

        In case of a :class:`~odoo.fields.One2many` relation, one new record
        is created in the comodel for every record in ``self`` such that every
        record in ``self`` is linked to exactly one of the new records.

        Return the command triple :samp:`(CREATE, 0, {values})`
        """
        return (cls.CREATE, 0, values)

    @classmethod
    def update(cls, id: int, values: ValuesType) -> CommandValue:
        """
        Write ``values`` on the related record.

        Return the command triple :samp:`(UPDATE, {id}, {values})`
        """
        return (cls.UPDATE, id, values)

    @classmethod
    def delete(cls, id: int) -> CommandValue:
        """
        Remove the related record from the database and remove its relation
        with ``self``.

        In case of a :class:`~odoo.fields.Many2many` relation, removing the
        record from the database may be prevented if it is still linked to
        other records.

        Return the command triple :samp:`(DELETE, {id}, 0)`
        """
        return (cls.DELETE, id, 0)

    @classmethod
    def unlink(cls, id: int) -> CommandValue:
        """
        Remove the relation between ``self`` and the related record.

        In case of a :class:`~odoo.fields.One2many` relation, the given record
        is deleted from the database if the inverse field is set as
        ``ondelete='cascade'``. Otherwise, the value of the inverse field is
        set to False and the record is kept.

        Return the command triple :samp:`(UNLINK, {id}, 0)`
        """
        return (cls.UNLINK, id, 0)

    @classmethod
    def link(cls, id: int) -> CommandValue:
        """
        Add a relation between ``self`` and the related record.

        Return the command triple :samp:`(LINK, {id}, 0)`
        """
        return (cls.LINK, id, 0)

    @classmethod
    def clear(cls) -> CommandValue:
        """
        Remove all records from the relation with ``self``. It behaves like
        executing the `unlink` command on every record.

        Return the command triple :samp:`(CLEAR, 0, 0)`
        """
        return (cls.CLEAR, 0, 0)

    @classmethod
    def set(cls, ids: Collection[int]) -> CommandValue:
        """
        Replace the current relations of ``self`` by the given ones. It behaves
        like executing the ``unlink`` command on every removed relation then
        executing the ``link`` command on every new relation.

        Return the command triple :samp:`(SET, 0, {ids})`
        """
        return (cls.SET, 0, ids)


if typing.TYPE_CHECKING:
    CommandValue = tuple[Command, int, typing.Literal[0] | ValuesType | Collection[int]]
