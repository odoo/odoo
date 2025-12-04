# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
from collections import defaultdict, UserList
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
    if not params.get_bool("mail.use_twilio_rtc_servers"):
        return None, None
    account_sid = params.get_str("mail.twilio_account_sid")
    auth_token = params.get_str("mail.twilio_account_token")
    return account_sid, auth_token


def get_sfu_url(env) -> str | None:
    params = env["ir.config_parameter"].sudo()
    sfu_url = params.get_str("mail.sfu_server_url") if params.get_bool("mail.use_sfu_server") else None
    if not sfu_url:
        sfu_url = os.getenv("ODOO_SFU_URL")
    if sfu_url:
        return sfu_url.rstrip("/")


def get_sfu_key(env) -> str | None:
    sfu_key = env['ir.config_parameter'].sudo().get_str('mail.sfu_server_key')
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

NO_VALUE = object()

class Store:
    """Helper to build a dict of data for sending to web client.
    It supports merging of data from multiple sources, either through list extend or dict update.
    The keys of data are the name of models as defined in mail JS code, and the values are any
    format supported by store.insert() method (single dict or list of dict for each model name)."""

    def __init__(self, bus_channel=None, bus_subchannel=None):
        self.data = {}
        self.data_id = None
        self.target = Store.Target(bus_channel, bus_subchannel)

    def add(self, records, fields, *, as_thread=False, fields_params=None):
        """Add records to the store. Data is coming from _to_store() method of the model if it is
        defined, and fallbacks to _read_format() otherwise.
        Fields can be defined in multiple ways:
        - as a string: the name of a method on the records that will be called with a Store.FieldList
          as first argument, and optional fields_params as other arguments.
        - as a callable: a function that will be called with a Store.FieldList as first argument.
        - as a list: list of field names.
        - as a dict: mapping of field names to static values.
        Relations are defined with StoreField.one() or StoreField.many() instead of a field name as
        string. Non-relation fields can also be defined with StoreField.attr() rather than simple
        string to provide extra parameters.

        Use case: to add records and their fields to store. This is the preferred method.
        """
        if not records:
            return self
        assert isinstance(records, models.Model)
        field_list = Store._format_fields(fields, self.target, records, fields_params)
        if not as_thread and hasattr(records, "_to_store"):
            records._to_store(self, field_list)
        else:
            self.add_records_fields(field_list, as_thread=as_thread)
        return self

    def add_global_values(self, field_fn=None, /, **values):
        """Add global values to the store. Global values are stored in the Store singleton
        (mail.store service) in the client side.

        Use case: to add global values."""
        assert not field_fn or not values
        self.add_singleton_values("Store", field_fn or values)
        return self

    def add_model_values(self, model_name, values):
        """Add values to a model in the store.

        Use case: to add values to JS records that don't have a corresponding Python record.
        Note: for python records adding model values is discouraged in favor of using Store.add().
        """
        if not values:
            return self
        data_list = []
        self._add_abstract_fields_value(Store._format_fields(values, self.target), data_list)
        index = self._get_record_index(model_name, data_list)
        self._ensure_record_at_index(model_name, index)
        for data in data_list:
            self._add_values(data, model_name, index)
        if "_DELETE" in self.data[model_name][index]:
            del self.data[model_name][index]["_DELETE"]
        return self

    def add_records_fields(self, field_list, as_thread=False):
        """Same as Store.add() but without calling _to_store().

        Use case: to add fields from inside _to_store() methods to avoid recursive code.
        Note: in all other cases, Store.add() should be called instead.
        """
        if not field_list or not field_list.records:
            return self
        for record, record_data_list in self._get_records_data_list(field_list).items():
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
        data_list = []
        self._add_abstract_fields_value(Store._format_fields(values, self.target), data_list)
        ids = ids_by_model[model_name]
        assert not ids
        if model_name not in self.data:
            self.data[model_name] = {}
        for data in data_list:
            self._add_values(data, model_name)
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
            index = self._get_record_index(model_name, [values])
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

    def resolve_data_request(self, values=None):
        """Add values to the store for the current data request.

        Use case: resolve a specific data request from a client."""
        if not self.data_id:
            return self
        data_list = []
        self._add_abstract_fields_value(Store._format_fields(values or [{}], self.target), data_list)
        for data in data_list:
            self.add_model_values("DataResponse", {"id": self.data_id, "_resolve": True, **data})
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

    @staticmethod
    def _format_fields(fields, target, records=None, fields_params=None):
        field_list = Store.FieldList()
        field_list.target = target
        field_list.records = records
        if isinstance(fields, str) and (method := Store._get_fields_method(records, fields)):
            method(field_list, **(fields_params or {}))
        elif callable(fields):
            fields(field_list)
        elif isinstance(fields, dict):
            field_list.extend(Store.Attr(key, value) for key, value in fields.items())
        elif isinstance(fields, (list, Store.FieldList)):
            field_list.extend(fields)  # prevent mutation of original list
        else:
            raise TypeError(f"unexpected fields format: '{fields}' for records: '{records}'")
        return field_list

    @staticmethod
    def _get_fields_method(records, method_name):
        if (
            isinstance(records, models.Model)
            and hasattr(records, method_name)
            and method_name.startswith("_store_")
            and method_name.endswith("_fields")
        ):
            # getattr: only allowed on recordsets for methods starting with _store_ and ending with _fields
            return getattr(records, method_name)
        return None

    def _get_records_data_list(self, field_list):
        abstract_fields = [field for field in field_list if isinstance(field, (dict, Store.Attr))]
        records_data_list = {
            record: [data]
            for record, data in zip(
                field_list.records,
                field_list.records._read_format(
                    [f for f in field_list if f not in abstract_fields],
                    load=False,
                ),
            )
        }
        for record, record_data_list in records_data_list.items():
            self._add_abstract_fields_value(abstract_fields, record_data_list, record)
        return records_data_list

    def _add_abstract_fields_value(self, abstract_fields, data_list, record=None):
        for field in abstract_fields:
            if isinstance(field, dict):
                data_list.append(field)
            elif not field.predicate or field.predicate(record):
                try:
                    data_list.append(
                        {field.field_name: field._get_value(record, target=self.target)},
                    )
                except MissingError:
                    break

    def _get_record_index(self, model_name, data_list):
        # regroup indentifying fields into values as they might be spread accross data_list entries
        values = {k: v for data in data_list if isinstance(data, dict) for k, v in data.items()}
        ids = ids_by_model[model_name]
        for i in ids:
            assert values.get(i), f"missing id {i} in {model_name}: {values}"
        return tuple(values[i] for i in ids)

    @staticmethod
    def _get_one_id(record, as_thread):
        if not record:
            return False
        if as_thread:
            return {"id": record.id, "model": record._name}
        if record._name == "discuss.channel":
            return {"id": record.id, "model": "discuss.channel"}
        return record.id

    @staticmethod
    def get_field_name(field_description):
        """Get the field name from a field description."""
        if isinstance(field_description, Store.Attr):
            return field_description.field_name
        return field_description

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

    class Attr:
        """Attribute to be added for each record. The value can be a static value or a function
        to compute the value, receiving the record as argument.

        Use case: to add a value when it does not come directly from a field.
        Note: when a static value is given to a recordset, the same value is set on all records.
        """

        def __init__(self, field_name, value=NO_VALUE, *, predicate=None, sudo=False):
            self.field_name = field_name
            self.predicate = predicate
            self.sudo = sudo
            self.value = value

        def _get_value(self, record, *, target=None):
            if self.value is NO_VALUE and record is not None and self.field_name in record._fields:
                return (record.sudo() if self.sudo else record)[self.field_name]
            if callable(self.value):
                if record is None:
                    return self.value()
                return self.value(record)
            if self.value is NO_VALUE:
                return None
            return self.value

    class Relation(Attr):
        """Flags a record or field name to be added to the store in a relation."""

        def __init__(
            self,
            records_or_field_name,
            fields,
            /,
            *,
            as_thread=False,
            dynamic_fields=None,
            fields_params=None,
            only_data=False,
            predicate=None,
            sudo=False,
            value=NO_VALUE,
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
            self.fields_params = fields_params
            self.only_data = only_data

        def _get_value(self, record, *, target=None):
            records = super()._get_value(record, target=target)
            if records is None and self.value is NO_VALUE:
                res_model_field = "res_model" if "res_model" in record._fields else "model"
                if self.field_name == "thread" and "thread" not in record._fields:
                    if (res_model := record[res_model_field]) and (res_id := record["res_id"]):
                        records = record.env[res_model].browse(res_id)
            return self._copy_with_records(records, calling_record=record, target=target)

        def _copy_with_records(self, records, calling_record, target):
            """Returns a new relation with the given records instead of the field name."""
            assert self.field_name and self.records is None
            assert not self.dynamic_fields or calling_record
            if records:
                field_list = Store._format_fields(self.fields, target, records, self.fields_params)
                if self.dynamic_fields:
                    if (
                        isinstance(self.dynamic_fields, str)
                        and (method := Store._get_fields_method(calling_record, self.dynamic_fields))
                    ):
                        # getattr: only allowed on recordsets for methods starting with _store_ and ending with _fields
                        method(field_list)
                    elif callable(self.dynamic_fields):
                        self.dynamic_fields(field_list, calling_record)
                    else:
                        raise TypeError(f"unexpected dynamic_fields format: '{self.dynamic_fields}'")
            else:
                field_list = []  # avoid calling field methods (which potentially does queries) on empty records
            return self.__class__(
                records,
                field_list,
                as_thread=self.as_thread,
                fields_params=self.fields_params,
                only_data=self.only_data,
            )

        def _add_to_store(self, store, target, key):
            """Add the current relation to the given store at target[key]."""
            store.add(self.records, self.fields, as_thread=self.as_thread)

    class One(Relation):
        """Flags a record or field name to be added to the store in a One relation."""

        def __init__(
            self,
            record_or_field_name,
            fields,
            /,
            *,
            as_thread=False,
            dynamic_fields=None,
            fields_params=None,
            only_data=False,
            predicate=None,
            sudo=False,
            value=NO_VALUE,
        ):
            super().__init__(
                record_or_field_name,
                fields,
                as_thread=as_thread,
                dynamic_fields=dynamic_fields,
                fields_params=fields_params,
                only_data=only_data,
                predicate=predicate,
                sudo=sudo,
                value=value,
            )
            assert not self.records or len(self.records) == 1, f"One received {self.records}"

        def _add_to_store(self, store: "Store", target, key):
            super()._add_to_store(store, target, key)
            if not self.only_data:
                target[key] = Store._get_one_id(self.records, self.as_thread)

    class Many(Relation):
        """Flags records or field name to be added to the store in a Many relation.
        - mode: "REPLACE" (default), "ADD", or "DELETE"."""

        def __init__(
            self,
            records_or_field_name,
            fields,
            /,
            *,
            mode="REPLACE",
            as_thread=False,
            dynamic_fields=None,
            fields_params=None,
            only_data=False,
            predicate=None,
            sort=None,
            sudo=False,
            value=NO_VALUE,
        ):
            super().__init__(
                records_or_field_name,
                fields,
                as_thread=as_thread,
                dynamic_fields=dynamic_fields,
                fields_params=fields_params,
                only_data=only_data,
                predicate=predicate,
                sudo=sudo,
                value=value,
            )
            self.mode = mode
            self.sort = sort

        def _copy_with_records(self, records, calling_record, target):
            if records is None:
                records = []
            res = super()._copy_with_records(records, calling_record, target)
            res.mode = self.mode
            res.sort = self.sort
            return res

        def _add_to_store(self, store: "Store", target, key):
            self._sort_recods()
            super()._add_to_store(store, target, key)
            if not self.only_data and (self.records or self.mode == "REPLACE"):
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
                res = [Store._get_one_id(record, self.as_thread) for record in self.records]
            if self.mode == "ADD":
                res = [("ADD", res)]
            elif self.mode == "DELETE":
                res = [("DELETE", res)]
            return res

        def _sort_recods(self):
            if self.sort:
                self.records = self.records.sorted(self.sort)
                self.sort = None

    class FieldList(UserList):
        """Helper to provide short syntax for building a list of field definitions for a specific
        store.add call (with given records and target)."""
        # records for which the field list will apply. Useful to pre-compute values in batch.
        records = None
        # Store.Target of the field list. Useful to adapt fields depending on the receivers.
        target = None

        def attr(self, field_name, value=NO_VALUE, *, predicate=None, sudo=False):
            """Add an attribute to the field list."""
            if self.records is not None and value is NO_VALUE and predicate is None and not sudo:
                self.append(field_name)
            else:
                self.append(Store.Attr(field_name, value=value, predicate=predicate, sudo=sudo))

        def from_method(self, method_name, **fields_params):
            """Add fields coming from a method on the records to the field list."""
            if (method := Store._get_fields_method(self.records, method_name)):
                method(self, **fields_params)
            else:
                raise TypeError(
                    f"unexpected method name format: '{method_name}' for records: '{self.records}'",
                )

        def one(self, record_or_field_name, fields, /, *args, **kwargs):
            """Add a x2one relation to the field list."""
            self.append(Store.One(record_or_field_name, fields, *args, **kwargs))

        def many(self, records_or_field_name, fields, /, *args, **kwargs):
            """Add a x2many relation to the field list."""
            self.append(Store.Many(records_or_field_name, fields, *args, **kwargs))

        def is_for_current_user(self):
            """Return whether the current target is the current user or guest of the given env.
            If there is no target at all, this is always True."""
            if self.target.channel is None and self.target.subchannel is None:
                return True
            env = self.records.env
            user = self.target_user()
            guest = self.target_guest()
            return self.target.subchannel is None and (
                (user and user == env.user and not env.user._is_public())
                or (guest and guest == env["mail.guest"]._get_guest_from_context())
            )

        def is_for_internal_users(self):
            """Return whether the current target implies the information will only be sent to
            internal users. If there is no target at all, the check is based on the current
            user of the env."""
            env = self.records.env
            bus_record = self.target.channel
            if bus_record is None and self.target.subchannel is None:
                bus_record = env.user
            return (
                isinstance(bus_record, env.registry["res.users"])
                and self.target.subchannel is None
                and bus_record._is_internal()
            ) or (
                isinstance(bus_record, env.registry["discuss.channel"])
                and (
                    self.target.subchannel == "internal_users"
                    or (
                        bus_record.channel_type == "channel"
                        and env.ref("base.group_user") in bus_record.group_public_id.all_implied_ids
                    )
                )
            ) or (
                isinstance(bus_record, env.registry["res.groups"])
                and env.ref("base.group_user") in bus_record.all_implied_ids
            )

        def target_guest(self):
            """Return target guest (if any). Target guest is either the current bus target if the
            bus is actually targetting a guest, or the current guest from env if there is no bus
            target at all but there is a guest in the env.
            """
            env = self.records.env
            records = self.target.channel
            if self.target.channel is None and self.target.subchannel is None:
                records = env["mail.guest"]._get_guest_from_context()
            return records if isinstance(records, env.registry["mail.guest"]) else env["mail.guest"]

        def target_user(self):
            """Return target user (if any). Target user is either the current bus target if the
            bus is actually targetting a user, or the current user from env if there is no bus
            target at all but there is a user in the env."""
            env = self.records.env
            records = self.target.channel
            if self.target.channel is None and self.target.subchannel is None:
                records = env.user
            return records if isinstance(records, env.registry["res.users"]) else env["res.users"]
