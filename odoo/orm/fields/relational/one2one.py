import typing
from typing import override

from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import SENTINEL, Sentinel

from ._commands import CommandDelta
from .many2one import Many2one
from .one2many import One2many

_debug = DebugLog(__name__)

if typing.TYPE_CHECKING:
    from collections.abc import Sequence

    from ..._typing import CommandValue
    from ...models import BaseModel


class One2one(One2many):
    """The one record of `comodel_name` whose `inverse_name` names this one.

    The many2one on the comodel is the stored fact and must carry
    `index="unique"`, so the database holds the cardinality. Read as a
    singleton recordset. Writing a record points its inverse here; the record
    that held the seat before is released when its inverse is optional and
    refused when it is required, because a one2one moves nothing silently.
    """

    is_one2one = True

    def __init__(
        self,
        comodel_name: str | Sentinel = SENTINEL,
        inverse_name: str | Sentinel = SENTINEL,
        string: str | Sentinel = SENTINEL,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(
            comodel_name=comodel_name,
            inverse_name=inverse_name,
            string=string,
            **kwargs,
        )

    @override
    def setup_nonrelated(self, model: BaseModel) -> None:
        super().setup_nonrelated(model)
        if not self.inverse_name or model._abstract:
            return
        comodel = model.env[self.comodel_name]
        inverse = comodel._fields[self.inverse_name]
        if not isinstance(inverse, Many2one):
            raise TypeError(
                f"{self}: {self.comodel_name}.{self.inverse_name} is a "
                f"{inverse.type}; a One2one inverts a many2one."
            )
        if inverse.store and inverse.index != "unique":
            raise TypeError(
                f"{self}: {self.comodel_name}.{self.inverse_name} must declare "
                f'index="unique"; a one2one is held by the database.'
            )

    def _fold_target(
        self, model: BaseModel, commands: list[CommandValue]
    ) -> tuple[CommandDelta, typing.Any, bool]:
        delta = CommandDelta.fold(commands, superseding=True)
        targets = list(delta.set_ids) if delta.replaced else list(delta.linked)
        if len(targets) > 1 or (targets and delta.created) or len(delta.created) > 1:
            _debug.logic(
                "field.one2one.refused",
                reason="several_targets",
                field=self.name,
                targets=len(targets),
                created=len(delta.created),
            )
            raise UserError(
                model.env._(
                    "%(field)s takes one record; several were given.",
                    field=self.string or self.name,
                )
            )
        target = targets[0] if targets else None
        releases = delta.replaced or bool(delta.unlinked) or bool(delta.deleted)
        return delta, target, releases

    @override
    def write_real(
        self,
        records_commands_list: Sequence[tuple[BaseModel, list[CommandValue]]],
        create: bool = False,
    ) -> None:
        if not records_commands_list:
            return
        model, comodel = self._get_writer_models(records_commands_list)
        inverse = self._get_inverse_name()
        inverse_field = comodel._fields[inverse]
        for recs, commands in records_commands_list:
            delta, target, releases = self._fold_target(model, commands)
            if len(recs) > 1 and (target or delta.created):
                _debug.logic(
                    "field.one2one.refused",
                    reason="shared_target",
                    field=self.name,
                    records=recs,
                )
                raise UserError(
                    model.env._(
                        "%(field)s: one record cannot be shared by several %(model)s.",
                        field=self.string or self.name,
                        model=model._description,
                    )
                )
            for line_id, vals in delta.updated:
                comodel.browse((line_id,)).write(vals)
            if delta.deleted:
                comodel.browse(list(delta.deleted)).unlink()
            for record in recs:
                current = record[self.name]
                if releases and current and current.id != target:
                    if inverse_field.required:
                        _debug.logic(
                            "field.one2one.refused",
                            reason="required_inverse",
                            field=self.name,
                            record=record,
                            current=current,
                        )
                        raise UserError(
                            model.env._(
                                "%(record)s already is %(current)s's %(field)s, which "
                                "cannot be left without one.",
                                record=record.display_name,
                                current=current.display_name,
                                field=self.string or self.name,
                            )
                        )
                    current[inverse] = False
                    # The seat is released in the database before the next
                    # holder takes it: the unique index checks each UPDATE.
                    current.flush_recordset([inverse])
                    _debug.lifecycle(
                        "field.one2one.released", field=self.name, released=current
                    )
                if target and current.id != target:
                    line = comodel.browse(target)
                    holder = line[inverse]
                    if holder and holder != record:
                        _debug.logic(
                            "field.one2one.refused",
                            reason="taken",
                            field=self.name,
                            line=line,
                            holder=holder,
                        )
                        raise UserError(
                            model.env._(
                                "%(line)s already belongs to %(holder)s.",
                                line=line.display_name,
                                holder=holder.display_name,
                            )
                        )
                    line[inverse] = record
                for _ref, vals in delta.created:
                    comodel.create({**vals, inverse: record.id})
            _debug.logic(
                "field.one2one.write",
                model=self.model_name,
                field=self.name,
                records=len(recs),
                target=target,
                released=releases,
            )
