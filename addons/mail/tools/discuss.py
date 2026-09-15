import os
import typing
from collections import defaultdict
from collections.abc import Callable
from datetime import date, datetime
from functools import wraps
from itertools import starmap
from typing import Any, Literal, Self

from markupsafe import Markup
from werkzeug.exceptions import NotFound

import odoo
from odoo import models
from odoo.exceptions import MissingError
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.tools import groupby

from odoo.addons.bus.websocket import wsrequest

if typing.TYPE_CHECKING:
    from odoo.api import Environment

_debug = DebugLog(__name__)

EMPTY_EDIT_MARKER = '<span class="o-mail-Message-edited"></span>'

type StoreFieldSpec = str | Store.Attr | dict[str, Any]
type StoreFieldsInput = StoreFieldSpec | list[StoreFieldSpec] | None


def add_guest_to_context[F: Callable](func: F) -> F:
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        req = request or wsrequest
        token = req.cookies.get(req.env["mail.guest"]._cookie_name, "")
        guest = req.env["mail.guest"]._get_guest_from_token(token)
        if guest and not guest.sudo().timezone and not req.env.cr.readonly:
            timezone = req.env["mail.guest"]._get_timezone_from_request(req)
            if timezone:
                guest._update_timezone(timezone)
        if guest:
            _debug.logic("guest_in_context", guest=guest.id, route=func.__name__)
            req.update_context(guest=guest)
            if isinstance(self, models.BaseModel):
                self = self.with_context(guest=guest)
        return func(self, *args, **kwargs)

    return wrapper


def to_record_id(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise NotFound
    try:
        return int(value)
    except ValueError:
        raise NotFound from None


def to_record_ids(values: Any) -> list[int]:
    if values is None:
        return []
    if isinstance(values, str) or not isinstance(values, (list, tuple)):
        raise NotFound
    return [to_record_id(value) for value in values]


def get_twilio_credentials(env: Environment) -> tuple[str | None, str | None]:
    params = env["ir.config_parameter"].sudo()
    if not params.get_param("mail.use_twilio_rtc_servers"):
        return None, None
    account_sid = params.get_param("mail.twilio_account_sid")
    auth_token = env["credential.credential"]._get_system_secret(
        "mail.twilio_account_token"
    )
    return account_sid, auth_token


def get_sfu_url(env: Environment) -> str | None:
    params = env["ir.config_parameter"].sudo()
    sfu_url = (
        params.get_param("mail.sfu_server_url")
        if params.get_param("mail.use_sfu_server")
        else None
    )
    if not sfu_url:
        sfu_url = os.getenv("ODOO_SFU_URL")
    _debug.logic(
        "sfu_url",
        configured=bool(sfu_url),
        by="env" if os.getenv("ODOO_SFU_URL") else "param",
    )
    if sfu_url:
        return sfu_url.rstrip("/")
    return None


def get_sfu_key(env: Environment) -> str | None:
    sfu_key = env["credential.credential"]._get_system_secret("mail.sfu_server_key")
    if not sfu_key:
        return os.getenv("ODOO_SFU_KEY")
    return sfu_key


ids_by_model: defaultdict[str, tuple[str, ...]] = defaultdict(lambda: ("id",))
ids_by_model.update(
    {
        "DiscussApp": (),
        "mixin.mail.thread": ("model", "id"),
        "MessageReactions": ("message", "content"),
        "Rtc": (),
        "Store": (),
    }
)


class Store:
    def __init__(
        self,
        bus_channel: models.Model | None = None,
        bus_subchannel: str | None = None,
    ) -> None:
        self.data: dict[str, Any] = {}
        self.data_id: int | str | None = None
        self.target = Store.Target(bus_channel, bus_subchannel)

    def add(
        self,
        records: models.Model,
        fields: StoreFieldsInput = None,
        extra_fields: StoreFieldsInput = None,
        as_thread: bool = False,
        **kwargs,
    ) -> Self:
        if not records:
            return self
        assert isinstance(records, models.Model)
        if fields is None:
            fields = [] if as_thread else records._to_store_defaults(self.target)
        fields = self._format_fields(records, fields) + self._format_fields(
            records, extra_fields
        )
        if as_thread:
            records._thread_to_store(self, fields, **kwargs)
        else:
            records._to_store(self, fields, **kwargs)
        return self

    def add_global_values(self, **values) -> Self:
        self.add_singleton_values("Store", values)
        return self

    def add_model_values(self, model_name: str, values: dict[str, Any]) -> Self:
        if not values:
            return self
        assert ids_by_model[model_name], (
            f"{model_name} is a singleton: use add_singleton_values()"
        )
        index = self._get_record_index(model_name, values)
        self._add_record_at_index(model_name, index)
        self._add_values(values, model_name, index)
        if "_DELETE" in self.data[model_name][index]:
            del self.data[model_name][index]["_DELETE"]
        return self

    def add_records_fields(
        self,
        records: models.Model,
        fields: StoreFieldsInput,
        as_thread: bool = False,
    ) -> Self:
        if not records:
            return self
        assert isinstance(records, models.Model)
        if not fields:
            return self
        fields = self._format_fields(records, fields)
        for record, record_data_list in self._get_records_data_list(records, fields):
            for record_data in record_data_list:
                if as_thread:
                    self.add_model_values(
                        "mixin.mail.thread",
                        {"id": record.id, "model": record._name, **record_data},
                    )
                else:
                    self.add_model_values(
                        record._name, {"id": record.id, **record_data}
                    )
        return self

    def add_singleton_values(self, model_name: str, values: dict[str, Any]) -> Self:
        if not values:
            return self
        ids = ids_by_model[model_name]
        assert not ids
        assert isinstance(values, dict)
        if model_name not in self.data:
            self.data[model_name] = {}
        self._add_values(values, model_name)
        return self

    def add_deletion(self, records: models.Model, as_thread: bool = False) -> Self:
        if not records:
            return self
        assert isinstance(records, models.Model)
        model_name = "mixin.mail.thread" if as_thread else records._name
        for record in records:
            values = (
                {"id": record.id}
                if not as_thread
                else {"id": record.id, "model": record._name}
            )
            index = self._get_record_index(model_name, values)
            self._add_record_at_index(model_name, index)
            self._add_values(values, model_name, index)
            self.data[model_name][index]["_DELETE"] = True
        return self

    def get_result(self) -> dict[str, Any]:
        res: dict[str, Any] = {}
        for model_name, records in sorted(self.data.items()):
            if not ids_by_model[model_name]:
                res[model_name] = dict(sorted(records.items()))
            else:
                res[model_name] = [
                    dict(sorted(record.items())) for record in records.values()
                ]
        return res

    def bus_send(self, notification_type: str = "mail.record/insert", /) -> None:
        assert self.target.channel is not None, (
            "Missing `bus_channel`. Pass it to the `Store` constructor to use `bus_send`."
        )
        if res := self.get_result():
            _debug.pipeline(
                "bus_send",
                notification_type=notification_type,
                channel=self.target.channel._name,
                models=sorted(res),
                records=sum(len(v) for v in res.values()),
            )
            self.target.channel._bus_send(
                notification_type, res, subchannel=self.target.subchannel
            )

    def resolve_data_request(self, **values) -> Self:
        if not self.data_id:
            return self
        self.add_model_values(
            "DataResponse", {"id": self.data_id, "_resolve": True, **values}
        )
        return self

    def _add_values(
        self,
        values: dict[str, Any],
        model_name: str,
        index: tuple[Any, ...] | None = None,
    ) -> None:
        target = (
            self.data[model_name][index] if index is not None else self.data[model_name]
        )
        for key, val in values.items():
            assert key != "_DELETE", f"invalid key {key} in {model_name}: {values}"
            if isinstance(val, Store.Relation):
                val._add_to_store(self, target, key)
            elif isinstance(val, datetime):
                target[key] = odoo.fields.Datetime.to_string(val)
            elif isinstance(val, date):
                target[key] = odoo.fields.Date.to_string(val)
            elif isinstance(val, Markup):
                target[key] = ["markup", str(val)]
            else:
                target[key] = val

    def _add_record_at_index(self, model_name: str, index: tuple[Any, ...]) -> None:
        if model_name not in self.data:
            self.data[model_name] = {}
        if index not in self.data[model_name]:
            self.data[model_name][index] = {}

    def _format_fields(
        self, records: models.Model, fields: StoreFieldsInput
    ) -> list[StoreFieldSpec]:
        fields = Store._static_format_fields(fields)
        return [f for field in fields for f in records._field_store_repr(field)]

    @staticmethod
    def _static_format_fields(fields: StoreFieldsInput) -> list[StoreFieldSpec]:
        if fields is None:
            return []
        if isinstance(fields, dict):
            return list(starmap(Store.Attr, fields.items()))
        if not isinstance(fields, list):
            return [fields]
        return list(fields)

    def _get_records_data_list(
        self, records: models.Model, fields: list[StoreFieldSpec]
    ) -> list[tuple[models.Model, list[dict[str, Any]]]]:
        abstract_fields = [
            field for field in fields if isinstance(field, (dict, Store.Attr))
        ]
        data_by_id = {
            data_dict["id"]: data_dict
            for data_dict in records._read_format(
                [f for f in fields if f not in abstract_fields],
                load=False,
            )
        }
        records_data_list = []
        for record in records:
            data_dict = data_by_id.get(record.id)
            if data_dict is None:
                continue
            record_data_list = [data_dict]
            for field in abstract_fields:
                if isinstance(field, dict):
                    record_data_list.append(field)
                elif not field.predicate or field.predicate(record):
                    try:
                        record_data_list.append(
                            {field.field_name: field._get_value(record)}
                        )
                    except MissingError:
                        break
            records_data_list.append((record, record_data_list))
        return records_data_list

    def _get_record_index(
        self, model_name: str, values: dict[str, Any]
    ) -> tuple[Any, ...]:
        ids = ids_by_model[model_name]
        for i in ids:
            assert values.get(i), f"missing id {i} in {model_name}: {values}"
        return tuple(values[i] for i in ids)

    class Target:
        def __init__(
            self,
            channel: models.Model | None = None,
            subchannel: str | None = None,
        ) -> None:
            assert channel is None or isinstance(channel, models.Model), (
                f"channel should be None or a record: {channel}"
            )
            assert channel is None or len(channel) <= 1, (
                f"channel should be empty or should be a single record: {channel}"
            )
            self.channel = channel
            self.subchannel = subchannel

        def is_current_user(self, env: Environment) -> bool:
            if self.channel is None and self.subchannel is None:
                return True
            user = self.get_user(env)
            guest = self.get_guest(env)
            return self.subchannel is None and (
                (user and user == env.user and not env.user._is_public())
                or (guest and guest == env["mail.guest"]._get_guest_from_context())
            )

        def is_internal(self, env: Environment) -> bool:
            bus_record = self.channel
            if bus_record is None and self.subchannel is None:
                bus_record = env.user
            return (
                (
                    isinstance(bus_record, env.registry["res.users"])
                    and self.subchannel is None
                    and bus_record._is_internal()
                )
                or (
                    isinstance(bus_record, env.registry["discuss.channel"])
                    and (
                        self.subchannel == "internal_users"
                        or (
                            bus_record.channel_type == "channel"
                            and env.ref("base.group_user")
                            in bus_record.group_public_id.all_implied_ids
                        )
                    )
                )
                or (
                    isinstance(self.channel, env.registry["res.groups"])
                    and env.ref("base.group_user") in self.channel.implied_ids
                )
            )

        def get_guest(self, env: Environment) -> models.Model:
            records = self.channel
            if self.channel is None and self.subchannel is None:
                records = env["mail.guest"]._get_guest_from_context()
            return (
                records
                if isinstance(records, env.registry["mail.guest"])
                else env["mail.guest"]
            )

        def get_user(self, env: Environment) -> models.Model:
            records = self.channel
            if self.channel is None and self.subchannel is None:
                records = env.user
            return (
                records
                if isinstance(records, env.registry["res.users"])
                else env["res.users"]
            )

    class Attr:
        _requires_real_field = True

        def __init__(
            self,
            field_name: str | None,
            value: Any = None,
            *,
            predicate: Callable[[models.Model], bool] | None = None,
            sudo: bool = False,
        ) -> None:
            self.field_name = field_name
            self.predicate = predicate
            self.sudo = sudo
            self.value = value

        def _get_value(self, record: models.Model) -> Any:
            if self.value is None and self.field_name is not None:
                if self.field_name in record._fields:
                    return (record.sudo() if self.sudo else record)[self.field_name]
                if self._requires_real_field:
                    raise ValueError(
                        f"Store.Attr({self.field_name!r}) names no field on "
                        f"{record._name} and carries no value"
                    )
            if callable(self.value):
                return self.value(record)
            return self.value

    class Relation(Attr):
        _requires_real_field = False

        def __init__(
            self,
            records_or_field_name: str | models.Model | None,
            fields: StoreFieldsInput = None,
            *,
            as_thread: bool = False,
            dynamic_fields: Callable[[models.Model], list[StoreFieldSpec]]
            | None = None,
            only_data: bool = False,
            predicate: Callable[[models.Model], bool] | None = None,
            sudo: bool = False,
            value: Any = None,
            **kwargs,
        ) -> None:
            field_name = (
                records_or_field_name
                if isinstance(records_or_field_name, str)
                else None
            )
            super().__init__(field_name, predicate=predicate, sudo=sudo, value=value)
            assert not records_or_field_name or isinstance(
                records_or_field_name, (str, models.Model)
            ), (
                f"expected recordset, field name, or empty value for Relation: {records_or_field_name}"
            )
            self.records = (
                records_or_field_name
                if isinstance(records_or_field_name, models.Model)
                else None
            )
            assert self.records is None or dynamic_fields is None, (
                """dynamic_fields can only be set when field name is provided, not records. """
                f"""Records: {self.records}, dynamic_fields: {dynamic_fields}"""
            )
            self.as_thread = as_thread
            self.dynamic_fields = dynamic_fields
            self.fields = fields
            self.only_data = only_data
            self.kwargs = kwargs

        def _get_value(self, record: models.Model) -> Self:
            target = super()._get_value(record)
            if target is None:
                res_model_field = (
                    "res_model" if "res_model" in record._fields else "model"
                )
                if self.field_name == "thread" and "thread" not in record._fields:
                    if (
                        (res_model := record[res_model_field])
                        and (res_id := record["res_id"])
                        and res_model in record.env
                    ):
                        target = record.env[res_model].browse(res_id)
            return self._copy_with_records(target, calling_record=record)

        def _copy_with_records(
            self, records: models.Model | None, calling_record: models.Model
        ) -> Self:
            assert self.field_name and self.records is None
            assert not self.dynamic_fields or calling_record
            extra_fields = Store._static_format_fields(self.kwargs.get("extra_fields"))
            if self.dynamic_fields:
                extra_fields += self.dynamic_fields(calling_record)
            params = {
                "as_thread": self.as_thread,
                "extra_fields": extra_fields,
                "fields": self.fields,
                "only_data": self.only_data,
                **{
                    key: val
                    for key, val in self.kwargs.items()
                    if key != "extra_fields"
                },
            }
            return self.__class__(records, **params)

        def _add_to_store(self, store: Store, target: dict[str, Any], key: str) -> None:
            store.add(
                self.records, self.fields, as_thread=self.as_thread, **self.kwargs
            )

    class One(Relation):
        def __init__(
            self,
            record_or_field_name: str | models.Model | None,
            fields: StoreFieldsInput = None,
            *,
            as_thread: bool = False,
            dynamic_fields: Callable[[models.Model], list[StoreFieldSpec]]
            | None = None,
            only_data: bool = False,
            predicate: Callable[[models.Model], bool] | None = None,
            sudo: bool = False,
            value: Any = None,
            **kwargs,
        ) -> None:
            super().__init__(
                record_or_field_name,
                fields,
                as_thread=as_thread,
                dynamic_fields=dynamic_fields,
                only_data=only_data,
                predicate=predicate,
                sudo=sudo,
                value=value,
                **kwargs,
            )
            assert not self.records or len(self.records) == 1

        def _add_to_store(self, store: Store, target: dict[str, Any], key: str) -> None:
            super()._add_to_store(store, target, key)
            if not self.only_data:
                target[key] = self._get_id()

        def _get_id(self) -> dict[str, Any] | int | Literal[False]:
            if not self.records:
                return False
            if self.as_thread:
                return {"id": self.records.id, "model": self.records._name}
            if self.records._name == "discuss.channel":
                return {"id": self.records.id, "model": "discuss.channel"}
            return self.records.id

    class Many(Relation):
        def __init__(
            self,
            records_or_field_name: str | models.Model | None,
            fields: StoreFieldsInput = None,
            *,
            mode: Literal["REPLACE", "ADD", "DELETE"] = "REPLACE",
            as_thread: bool = False,
            dynamic_fields: Callable[[models.Model], list[StoreFieldSpec]]
            | None = None,
            only_data: bool = False,
            predicate: Callable[[models.Model], bool] | None = None,
            sort: Callable[[models.Model], Any] | str | None = None,
            sudo: bool = False,
            value: Any = None,
            **kwargs,
        ) -> None:
            super().__init__(
                records_or_field_name,
                fields,
                as_thread=as_thread,
                dynamic_fields=dynamic_fields,
                only_data=only_data,
                predicate=predicate,
                sudo=sudo,
                value=value,
                **kwargs,
            )
            self.mode = mode
            self.sort = sort

        def _copy_with_records(self, *args, **kwargs) -> Self:
            res = super()._copy_with_records(*args, **kwargs)
            res.mode = self.mode
            res.sort = self.sort
            return res

        def _add_to_store(self, store: Store, target: dict[str, Any], key: str) -> None:
            self._sort_records()
            super()._add_to_store(store, target, key)
            if not self.only_data:
                rel_val = self._get_id()
                target[key] = (
                    target[key] + rel_val
                    if key in target and self.mode != "REPLACE"
                    else rel_val
                )

        def _get_id(self) -> list[Any]:
            self._sort_records()
            if self.records._name == "mail.message.reaction":
                res = [
                    {"message": message.id, "content": content}
                    for (message, content), _ in groupby(
                        self.records, lambda r: (r.message_id, r.content)
                    )
                ]
            else:
                res = [
                    Store.One(record, as_thread=self.as_thread)._get_id()
                    for record in self.records
                ]
            if self.mode == "ADD":
                res = [("ADD", res)]
            elif self.mode == "DELETE":
                res = [("DELETE", res)]
            return res

        def _sort_records(self) -> None:
            if self.sort:
                self.records = self.records.sorted(self.sort)
                self.sort = None
