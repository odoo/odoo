from __future__ import annotations

import typing
import uuid
from collections import defaultdict

from odoo.libs.debug_log import DebugLog

if typing.TYPE_CHECKING:
    from .._typing import BaseModel, IdType
    from .environment import Environment

_debug = DebugLog(__name__)


class Xmlids:
    __slots__ = ()

    def of_records(self, records: BaseModel) -> dict[int, list[tuple[str, bool]]]:
        result: dict[int, list[tuple[str, bool]]] = defaultdict(list)
        if "ir.model.data" not in records.env.registry:
            return result
        for data in (
            records.env["ir.model.data"]
            .sudo()
            .search_read(
                [("model", "=", records._name), ("res_id", "in", records.ids)],
                ["module", "name", "res_id", "noupdate"],
                order="id",
            )
        ):
            result[data["res_id"]].append(
                (
                    f"{data['module']}.{data['name']}"
                    if data["module"]
                    else data["name"],
                    data["noupdate"],
                )
            )
        return result

    def records_of(self, records: BaseModel) -> BaseModel:
        if "ir.model.data" not in records.env.registry:
            return records.browse()
        return (
            records.env["ir.model.data"]
            .sudo()
            .with_context({})
            .search([("model", "=", records._name), ("res_id", "in", records.ids)])
        )

    def resolve(
        self, env: Environment, xml_ids: list[str], model: BaseModel
    ) -> list[tuple]:
        if not xml_ids:
            return []
        return env["ir.model.data"].sudo()._get_xmlids(xml_ids, model)

    def target(
        self, env: Environment, xml_id: str, raise_if_not_found: bool
    ) -> tuple[str, int] | tuple[typing.Literal[False], typing.Literal[False]]:
        if "ir.model.data" not in env.registry:
            if raise_if_not_found:
                raise ValueError(
                    f"No record found for unique ID {xml_id}: the registry has no "
                    f"ir.model.data model to resolve it"
                )
            return (False, False)
        return env["ir.model.data"]._xmlid_to_res_model_res_id(
            xml_id, raise_if_not_found=raise_if_not_found
        )

    def update(
        self, env: Environment, entries: list[dict], update: bool = False
    ) -> None:
        if not entries:
            return
        env["ir.model.data"].sudo()._update_xmlids(entries, update)

    def remove(self, env: Environment, ids: typing.Iterable[int]) -> None:
        env["ir.model.data"].sudo().browse(ids).unlink()

    def get_or_create_for_records(
        self, records: BaseModel, module: str
    ) -> dict[IdType, str]:
        xids: dict[IdType, str] = {
            res_id: names[0][0] for res_id, names in self.of_records(records).items()
        }
        missing = records.filtered(lambda r: r.id not in xids)
        if missing:
            entries = []
            for record in missing:
                name = f"{record._table}_{record.id}_{uuid.uuid4().hex[:8]}"
                xids[record.id] = f"{module}.{name}"
                entries.append(
                    {"xml_id": xids[record.id], "record": record, "noupdate": False}
                )
            self.update(records.env, entries)
        return xids

    def finish_load(self, env: Environment, updated_modules: typing.Any) -> None:
        with _debug.perf(
            "xmlids.finish_load",
            cr=getattr(env, "cr", None),
            modules=len(updated_modules) if updated_modules else 0,
        ):
            env["ir.model.data"]._process_end(updated_modules)


XMLIDS = Xmlids()
