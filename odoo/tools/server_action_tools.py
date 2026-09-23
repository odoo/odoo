from __future__ import annotations

import datetime as dt
import json as jsonlib
import re
from typing import Any

from odoo.exceptions import UserError
from odoo.libs.datetime import localize_standard, timezone
from odoo.libs.sql.utils import escape_psql

DATETIME = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:[ T](\d{1,2}):(\d{2})(?::\d{2})?)?$")
AMBIGUOUS_SHOWN = 6


class ServerActionTools:
    def __init__(self, env: Any) -> None:
        self._env = env

    def like(self, text: str | None) -> str:
        return escape_psql((text or "").strip())

    def find(
        self,
        model_name: str,
        name: str | None,
        domain: Any = (),
        archived: bool = False,
    ) -> Any:
        Model = self._env[model_name].with_context(active_test=not archived)
        name = (name or "").strip()
        if not name:
            return Model
        field = Model._rec_name or "name"
        pattern = self.like(name)
        base = list(domain or [])
        exact = Model.search([*base, (field, "=ilike", pattern)], limit=AMBIGUOUS_SHOWN)
        if len(exact) == 1:
            return exact
        found = exact or Model.search(
            [*base, (field, "ilike", pattern)], limit=AMBIGUOUS_SHOWN
        )
        if len(found) <= 1:
            return found
        raise UserError(
            self._env._(
                "'%(name)s' matches several records (%(names)s); say which one.",
                name=name,
                names=", ".join(found.mapped("display_name")),
            )
        )

    def date(self, value: Any) -> dt.date | None:
        if not value:
            return None
        if isinstance(value, dt.date):
            return value if not isinstance(value, dt.datetime) else value.date()
        try:
            return dt.date.fromisoformat(str(value).strip()[:10])
        except ValueError as error:
            raise UserError(self._env._("Unreadable date: %s", value)) from error

    def datetime(
        self,
        value: Any,
        default_time: str = "00:00",
        local: bool = True,
        tz: str | None = None,
    ) -> dt.datetime | None:
        if not value:
            return None
        match = DATETIME.match(str(value).strip())
        if not match:
            raise UserError(self._env._("Unreadable date and time: %s", value))
        day, hour, minute = match.groups()
        if hour is None:
            hour, minute = default_time.split(":")
        try:
            naive = dt.datetime.fromisoformat(f"{day} {int(hour):02d}:{minute}")
        except ValueError as error:
            raise UserError(
                self._env._("Unreadable date and time: %s", value)
            ) from error
        if not local:
            return naive
        zone = timezone(tz or self._env.user.tz or "UTC")
        return localize_standard(naive, zone).astimezone(dt.UTC).replace(tzinfo=None)

    def lines(self, rows: Any, extra: str = "unit") -> list[dict[str, Any]]:
        parsed = []
        for raw in rows or []:
            parts = [part.strip() for part in str(raw).split("|")]
            if not parts or not parts[0]:
                continue
            try:
                quantity = float(parts[1]) if len(parts) > 1 and parts[1] else 1.0
            except ValueError:
                quantity = 1.0
            parsed.append(
                {
                    "name": parts[0],
                    "quantity": quantity,
                    extra: parts[2] if len(parts) > 2 else "",
                }
            )
        return parsed

    def json(self, text: Any) -> dict[str, Any]:
        if isinstance(text, dict):
            return text
        try:
            data = jsonlib.loads(text or "{}")
        except ValueError as error:
            raise UserError(
                self._env._("Values must be a JSON object: %s", error)
            ) from error
        if not isinstance(data, dict):
            raise UserError(self._env._("Values must be a JSON object."))
        return data
