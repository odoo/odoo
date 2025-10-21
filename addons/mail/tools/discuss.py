# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
from collections import defaultdict
from datetime import date, datetime
from functools import wraps
from markupsafe import Markup

import odoo
from odoo import models
from odoo.exceptions import MissingError
from odoo.http import request
from odoo.tools import groupby
from odoo.addons.bus.websocket import wsrequest

def add_guest_to_context(func):
    """ Decorate a function to extract the guest from the request.
    The guest is then available on the context of the current
    request.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        req = request or wsrequest
        token = (
            req.cookies.get(req.env["mail.guest"]._cookie_name, "")
        )
        guest = req.env["mail.guest"]._get_guest_from_token(token)
        if guest and not guest.timezone and not req.env.cr.readonly:
            timezone = req.env["mail.guest"]._get_timezone_from_request(req)
            if timezone:
                guest._update_timezone(timezone)
        if guest:
            req.update_context(guest=guest)
            if isinstance(self, models.BaseModel):
                self = self.with_context(guest=guest)
        return func(self, *args, **kwargs)

    return wrapper


def get_twilio_credentials(env) -> tuple[str | None, str | None]:
    """
    To be overridable if we need to obtain credentials from another source.
    :return: tuple(account_sid: str, auth_token: str) or (None, None) if Twilio is disabled
    """
    params = env["ir.config_parameter"].sudo()
    if not params.get_param("mail.use_twilio_rtc_servers"):
        return None, None
    account_sid = params.get_param("mail.twilio_account_sid")
    auth_token = params.get_param("mail.twilio_account_token")
    return account_sid, auth_token


def get_sfu_url(env) -> str | None:
    params = env["ir.config_parameter"].sudo()
    sfu_url = params.get_param("mail.sfu_server_url") if params.get_param("mail.use_sfu_server") else None
    if not sfu_url:
        sfu_url = os.getenv("ODOO_SFU_URL")
    if sfu_url:
        return sfu_url.rstrip("/")


def get_sfu_key(env) -> str | None:
    sfu_key = env['ir.config_parameter'].sudo().get_param('mail.sfu_server_key')
    if not sfu_key:
        return os.getenv("ODOO_SFU_KEY")
    return sfu_key


ids_by_model = defaultdict(lambda: ("id",))
ids_by_model.update(
    {
        "DiscussApp": (),
        "mail.thread": ("model", "id"),
        "MessageReactions": ("message", "content"),
        "Rtc": (),
        "Store": (),
    }
)


class Store:
    """Helper to build a dict of data for sending to web client.
    It supports merging of data from multiple sources, either through list extend or dict update.
    The keys of data are the name of models as defined in mail JS code, and the values are any
    format supported by store.insert() method (single dict or list of dict for each model name)."""

    def __init__(self, bus_channel=None, bus_subchannel=None):
        self.data = {}
        self.data_id = None
        self.target = Store.Target(bus_channel, bus_subchannel)

    def add(self, records, fields=None, extra_fields=None, as_thread=False, **kwargs):
        """Add records to the store. Data is coming from _to_store() method of the model if it is
        defined, and fallbacks to _read_format() otherwise.
        Relations are defined with Store.One() or Store.Many() instead of a field name as string.

        Use case: to add records and their fields to store. This is the preferred method.
        """
        if not records:
            return self
        assert isinstance(records, models.Model)
        if fields is None:
            if as_thread:
                fields = []
            else:
                fields = (
                    records._to_store_defaults(self.target)
                    if hasattr(records, "_to_store_defaults")
                    else []
                )
        fields = self._format_fields(records, fields) + self._format_fields(records, extra_fields)
        if as_thread:
            if hasattr(records, "_thread_to_store"):
                records._thread_to_store(self, fields, **kwargs)
            else:
                assert not kwargs
                self.add_records_fields(records, fields, as_thread=True)
        else:
            if hasattr(records, "_to_store"):
                records._to_store(self, fields, **kwargs)
            else:
                assert not kwargs
                self.add_records_fields(records, fields)
        return self

    def add_global_values(self, **values):
        """Add global values to the store. Global values are stored in the Store singleton
        (mail.store service) in the client side.

        Use case: to add global values."""
        self.add_singleton_values("Store", values)
        return self

    def add_model_values(self, model_name, values):
        """Add values to a model in the store.

        Use case: to add values to JS records that don't have a corresponding Python record.
        Note: for python records adding model values is discouraged in favor of using Store.add().
        """
        if not values:
            return self
        index = self._get_record_index(model_name, values)
        self._ensure_record_at_index(model_name, index)
        self._add_values(values, model_name, index)
        if "_DELETE" in self.data[model_name][index]:
            del self.data[model_name][index]["_DELETE"]
        return self

    def add_records_fields(self, records, fields, as_thread=False):
        """Same as Store.add() but without calling _to_store().

        Use case: to add fields from inside _to_store() methods to avoid recursive code.
        Note: in all other cases, Store.add() should be called instead.
        """
        if not records:
            return self
        assert isinstance(records, models.Model)
        if not fields:
            return self
        fields = self._format_fields(records, fields)
        for record, record_data_list in zip(records, self._get_records_data_list(records, fields)):
            for record_data in record_data_list:
                if as_thread:
                    self.add_model_values(
                        "mail.thread", {"id": record.id, "model": record._name, **record_data},
                    )
                else:
                    self.add_model_values(record._name, {"id": record.id, **record_data})
        return self

    def add_singleton_values(self, model_name, values):
        """Add values to the store for a singleton model."""
        if not values:
            return self
        ids = ids_by_model[model_name]
        assert not ids
        assert isinstance(values, dict)
        if model_name not in self.data:
            self.data[model_name] = {}
        self._add_values(values, model_name)
        return self

    def delete(self, records, as_thread=False):
        """Delete records from the store."""
        if not records:
            return self
        assert isinstance(records, models.Model)
        model_name = "mail.thread" if as_thread else records._name
        for record in records:
            values = (
                {"id": record.id} if not as_thread else {"id": record.id, "model": record._name}
            )
            index = self._get_record_index(model_name, values)
            self._ensure_record_at_index(model_name, index)
            self._add_values(values, model_name, index)
            self.data[model_name][index]["_DELETE"] = True
        return self

    def get_result(self):
        """Gets resulting data built from adding all data together."""
        res = {}
        for model_name, records in sorted(self.data.items()):
            if not ids_by_model[model_name]:  # singleton
                res[model_name] = dict(sorted(records.items()))
            else:
                res[model_name] = [dict(sorted(record.items())) for record in records.values()]
        return res

    def bus_send(self, notification_type="mail.record/insert", /):
        assert self.target.channel is not None, (
            "Missing `bus_channel`. Pass it to the `Store` constructor to use `bus_send`."
        )
        if res := self.get_result():
            self.target.channel._bus_send(notification_type, res, subchannel=self.target.subchannel)

    def resolve_data_request(self, **values):
        """Add values to the store for the current data request.

        Use case: resolve a specific data request from a client."""
        if not self.data_id:
            return self
        self.add_model_values("DataResponse", {"id": self.data_id, "_resolve": True, **values})
        return self

    def _add_values(self, values, model_name, index=None):
        """Adds values to the store for a given model name and index."""
        target = self.data[model_name][index] if index else self.data[model_name]
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

    def _ensure_record_at_index(self, model_name, index):
        if model_name not in self.data:
            self.data[model_name] = {}
        if index not in self.data[model_name]:
            self.data[model_name][index] = {}

    def _format_fields(self, records, fields):
        fields = Store._static_format_fields(fields)
        if hasattr(records, "_field_store_repr"):
            return [f for field in fields for f in records._field_store_repr(field)]
        return fields

    @staticmethod
    def _static_format_fields(fields):
        if fields is None:
            return []
        if isinstance(fields, dict):
            return [Store.Attr(key, value) for key, value in fields.items()]
        if not isinstance(fields, list):
            return [fields]
        return list(fields)  # prevent mutation of original list

    def _get_records_data_list(self, records, fields):
        abstract_fields = [field for field in fields if isinstance(field, (dict, Store.Attr))]
        records_data_list = [
            [data_dict]
            for data_dict in records._read_format(
                [f for f in fields if f not in abstract_fields], load=False,
            )
        ]
        for record, record_data_list in zip(records, records_data_list):
            for field in abstract_fields:
                if isinstance(field, dict):
                    record_data_list.append(field)
                elif not field.predicate or field.predicate(record):
                    try:
                        record_data_list.append({field.field_name: field._get_value(record)})
                    except MissingError:
                        break
        return records_data_list

    def _get_record_index(self, model_name, values):
        ids = ids_by_model[model_name]
        for i in ids:
            assert values.get(i), f"missing id {i} in {model_name}: {values}"
        return tuple(values[i] for i in ids)

    class Target:
        """Target of the current store. Useful when information have to be added contextually
        depending on who is going to receive it."""

        def __init__(self, channel=None, subchannel=None):
            assert channel is None or isinstance(channel, models.Model), (
                f"channel should be None or a record: {channel}"
            )
            assert channel is None or len(channel) <= 1, (
                f"channel should be empty or should be a single record: {channel}"
            )
            self.channel = channel
            self.subchannel = subchannel

        def is_current_user(self, env):
            """Return whether the current target is the current user or guest of the given env.
            If there is no target at all, this is always True."""
            if self.channel is None and self.subchannel is None:
                return True
            user = self.get_user(env)
            guest = self.get_guest(env)
            return self.subchannel is None and (
                (user and user == env.user and not env.user._is_public())
                or (guest and guest == env["mail.guest"]._get_guest_from_context())
            )

        def is_internal(self, env):
            """Return whether the current target implies the information will only be sent to
            internal users. If there is no target at all, the check is based on the current
            user of the env."""
            bus_record = self.channel
            if bus_record is None and self.subchannel is None:
                bus_record = env.user
            return (
                isinstance(bus_record, env.registry["res.users"])
                and self.subchannel is None
                and bus_record._is_internal()
            ) or (
                isinstance(bus_record, env.registry["discuss.channel"])
                and (
                    self.subchannel == "internal_users"
                    or (
                        bus_record.channel_type == "channel"
                        and env.ref("base.group_user") in bus_record.group_public_id.all_implied_ids
                    )
                )
            )

        def get_guest(self, env):
            """Return target guest (if any). Target guest is either the current bus target if the
            bus is actually targetting a guest, or the current guest from env if there is no bus
            target at all but there is a guest in the env.
            """
            records = self.channel
            if self.channel is None and self.subchannel is None:
                records = env["mail.guest"]._get_guest_from_context()
            return records if isinstance(records, env.registry["mail.guest"]) else env["mail.guest"]

        def get_user(self, env):
            """Return target user (if any). Target user is either the current bus target if the
            bus is actually targetting a user, or the current user from env if there is no bus
            target at all but there is a user in the env."""
            records = self.channel
            if self.channel is None and self.subchannel is None:
                records = env.user
            return records if isinstance(records, env.registry["res.users"]) else env["res.users"]

    class Attr:
        """Attribute to be added for each record. The value can be a static value or a function
        to compute the value, receiving the record as argument.

        Use case: to add a value when it does not come directly from a field.
        Note: when a static value is given to a recordset, the same value is set on all records.
        """

        def __init__(self, field_name, value=None, *, predicate=None, sudo=False):
            self.field_name = field_name
            self.predicate = predicate
            self.sudo = sudo
            self.value = value

        def _get_value(self, record):
            if self.value is None and self.field_name in record._fields:
                return (record.sudo() if self.sudo else record)[self.field_name]
            if callable(self.value):
                return self.value(record)
            return self.value

    class Relation(Attr):
        """Flags a record or field name to be added to the store in a relation."""

        def __init__(
            self,
            records_or_field_name,
            fields=None,
            *,
            as_thread=False,
            dynamic_fields=None,
            only_data=False,
            predicate=None,
            sudo=False,
            value=None,
            **kwargs,
        ):
            field_name = records_or_field_name if isinstance(records_or_field_name, str) else None
            super().__init__(field_name, predicate=predicate, sudo=sudo, value=value)
            assert (
                not records_or_field_name
                or isinstance(records_or_field_name, (str, models.Model))
            ), f"expected recordset, field name, or empty value for Relation: {records_or_field_name}"
            self.records = (
                records_or_field_name if isinstance(records_or_field_name, models.Model) else None
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

        def _get_value(self, record):
            target = super()._get_value(record)
            if target is None:
                res_model_field = "res_model" if "res_model" in record._fields else "model"
                if self.field_name == "thread" and "thread" not in record._fields:
                    if (res_model := record[res_model_field]) and (res_id := record["res_id"]):
                        target = record.env[res_model].browse(res_id)
            return self._copy_with_records(target, calling_record=record)

        def _copy_with_records(self, records, calling_record):
            """Returns a new relation with the given records instead of the field name."""
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
                **{key: val for key, val in self.kwargs.items() if key != "extra_fields"},
            }
            return self.__class__(records, **params)

        def _add_to_store(self, store: "Store", target, key):
            """Add the current relation to the given store at target[key]."""
            store.add(self.records, self.fields, as_thread=self.as_thread, **self.kwargs)

    class One(Relation):
        """Flags a record or field name to be added to the store in a One relation."""

        def __init__(
            self,
            record_or_field_name,
            fields=None,
            *,
            as_thread=False,
            dynamic_fields=None,
            only_data=False,
            predicate=None,
            sudo=False,
            value=None,
            **kwargs,
        ):
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

        def _add_to_store(self, store: "Store", target, key):
            super()._add_to_store(store, target, key)
            if not self.only_data:
                target[key] = self._get_id()

        def _get_id(self):
            """Return the id that can be used to insert the current relation in the store."""
            if not self.records:
                return False
            if self.as_thread:
                return {"id": self.records.id, "model": self.records._name}
            if self.records._name == "discuss.channel":
                return {"id": self.records.id, "model": "discuss.channel"}
            return self.records.id

    class Many(Relation):
        """Flags records or field name to be added to the store in a Many relation.
        - mode: "REPLACE" (default), "ADD", or "DELETE"."""

        def __init__(
            self,
            records_or_field_name,
            fields=None,
            *,
            mode="REPLACE",
            as_thread=False,
            dynamic_fields=None,
            only_data=False,
            predicate=None,
            sort=None,
            sudo=False,
            value=None,
            **kwargs,
        ):
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

        def _copy_with_records(self, *args, **kwargs):
            res = super()._copy_with_records(*args, **kwargs)
            res.mode = self.mode
            res.sort = self.sort
            return res

        def _add_to_store(self, store: "Store", target, key):
            self._sort_recods()
            super()._add_to_store(store, target, key)
            if not self.only_data:
                rel_val = self._get_id()
                target[key] = (
                    target[key] + rel_val if key in target and self.mode != "REPLACE" else rel_val
                )

        def _get_id(self):
            """Return the ids that can be used to insert the current relation in the store."""
            self._sort_recods()
            if self.records._name == "mail.message.reaction":
                res = [
                    {"message": message.id, "content": content}
                    for (message, content), _ in groupby(
                        self.records, lambda r: (r.message_id, r.content)
                    )
                ]
            else:
                res = [
                    Store.One(record, as_thread=self.as_thread)._get_id() for record in self.records
                ]
            if self.mode == "ADD":
                res = [("ADD", res)]
            elif self.mode == "DELETE":
                res = [("DELETE", res)]
            return res

        def _sort_recods(self):
            if self.sort:
                self.records = self.records.sorted(self.sort)
                self.sort = None
