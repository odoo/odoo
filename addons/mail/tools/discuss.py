# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
import os
from collections import UserList, defaultdict
from contextlib import suppress
from datetime import date, datetime
from functools import partial, wraps
from itertools import product, repeat
from types import CellType, MethodType
from typing import Generic, TypeVar

from markupsafe import Markup

import odoo
from odoo import models
from odoo.exceptions import MissingError
from odoo.http import request, route
from odoo.tools.misc import hmac

from odoo.addons.bus.websocket import wsrequest

T = TypeVar("T")

_logger = logging.getLogger(__name__)


def add_guest_to_context(func):
    """ Decorate a function to extract the guest from the request.
    The guest is then available on the context of the current
    request.
    """

    @wraps(func)
    def add_guest_to_context__wrapper(self, *args, **kwargs):
        req = request or wsrequest
        if not req:
            raise NotImplementedError(
                self.env._("@add_guest_to_context must be called only within a request context."),
            )
        token = req.cookies.get(req.env["mail.guest"]._cookie_name)
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
    return add_guest_to_context__wrapper


def mail_route(*route_args, **route_kwargs):
    """Thin wrapper around ``route`` that adds guest context.

    This decorator is equivalent to applying, in order::

        @route(*route_args, **route_kwargs)
        @add_guest_to_context
    """

    def decorator(func):
        wrapped_func = add_guest_to_context(func)
        return route(*route_args, **route_kwargs)(wrapped_func)

    return decorator


def get_twilio_credentials(env) -> tuple[str | None, str | None]:
    """
    To be overridable if we need to obtain credentials from another source.
    :return: tuple(account_sid: str, auth_token: str) or (None, None) if Twilio is disabled
    """
    params = env["ir.config_parameter"].sudo()
    if not params.get_bool("mail.use_call_server") or not params.get_bool("mail.use_twilio_rtc_servers"):
        return None, None
    account_sid = params.get_str("mail.twilio_account_sid")
    auth_token = params.get_str("mail.twilio_account_token")
    return account_sid, auth_token


def get_sfu_url(env) -> str | None:
    params = env["ir.config_parameter"].sudo()
    use_sfu_setting = params.get_bool("mail.use_call_server") and params.get_bool("mail.use_sfu_server")
    sfu_url = params.get_str("mail.sfu_server_url") if use_sfu_setting else None
    if not sfu_url:
        sfu_url = os.getenv("ODOO_SFU_URL")
    if sfu_url:
        return sfu_url.rstrip("/")


def get_sfu_key(env) -> str | None:
    sfu_key = env['ir.config_parameter'].sudo().get_str('mail.sfu_server_key')
    if not sfu_key:
        return os.getenv("ODOO_SFU_KEY")
    return sfu_key


def get_derived_sfu_key(env, channel_id) -> str:
    digest = hmac(env(su=True), "discuss-sfu-channel-key", channel_id).encode()
    return base64.b64encode(digest).decode()


ids_by_model = defaultdict(lambda: ("id",))
ids_by_model.update(
    {
        "DiscussApp": (),
        "mail.thread": ("model", "id"),
        "Rtc": (),
        "Store": (),
    }
)

NO_VALUE = object()


def store_enqueue(func):
    """Wraps a Store method to postpone its execution until `Store._build_result()`."""

    @wraps(func)
    def store_enqueue__wrapper(store, *args, **kwargs):
        if func.__name__ == "resolve_data_request" and "data_id" not in kwargs:
            kwargs["data_id"] = store.data_id
        if not store.is_executing_operation_queue:
            store.operation_queue.append(lambda: func(store, *args, **kwargs))
            return store
        return func(store, *args, **kwargs)

    return store_enqueue__wrapper


class Store:
    """Helper to build a dict of data for sending to web client.
    It supports merging of data from multiple sources, either through list extend or dict
    update. The keys of data are the name of models as defined in mail JS code, and the
    values are any format supported by store.insert() method (single dict or list of dict
    for each model name).

    The store instance is then transformed to a dictionnary to be sent either by the HTTP
    or the bus stack. This dictionnary also includes information about the data version,
    which will be used by the client to distinguish stale from new data.

    If `bus_channel` is passed, the store will automatically be sent through the bus.
    """

    def __init__(
        self,
        bus_channel=None,
        bus_subchannel=None,
        *,
        notification_type=None,
        notification_payload=None,
    ):
        self.add_depth = 0
        self.already_done = set()
        self.field_lists_in_progress = defaultdict(list)
        self.data = defaultdict(lambda: defaultdict(dict))
        self.data_id = None
        self.is_executing_operation_queue = False
        self.operation_queue = []
        self.target = Store.Target(bus_channel, bus_subchannel)
        self._internal_store = None
        self._auto_send = True
        assert bus_channel is not None or not (notification_payload or notification_type), (
            "Notification parameters only make sense when a bus channel is passed."
        )
        if bus_channel:
            type_ = notification_type or "mail.record/insert"
            payload = (
                self
                if notification_payload is None
                else {**notification_payload, "store_data": self}
            )
            bus_channel._bus_send(type_, payload, subchannel=bus_subchannel)
            if bus_channel._name == "discuss.channel" and bus_subchannel != "internal_users":
                self._internal_store = Store(bus_channel, bus_subchannel="internal_users")

    @store_enqueue
    def add(self, records, fields, *, as_thread=False, fields_params=None, ignore_empty=False):
        """Add records to the store.

        Fields can be defined in multiple ways:

        - as a string: the name of a method on the records that will be called with a Store.FieldList
          as first argument, and optional fields_params as other arguments.
        - as a callable: a function that will be called with a Store.FieldList as first argument.
        - as a list: list of field names. Data for fields are coming from _read_format().
        - as a dict: mapping of field names to static values.

        Relations are defined with StoreField.one() or StoreField.many() instead of a field name as
        string. Non-relation fields can also be defined with StoreField.attr() rather than simple
        string to provide extra parameters.

        Use case: to add records and their fields to store. This is the preferred method.
        """
        if not records:
            return self
        cache = records.env.cr.precommit.data.get("mail.store.field_lists")
        key = None
        if cache is not None and isinstance(fields, str):
            key = (
                records.env,
                records._name,
                records._ids,
                fields,
                Store._deep_freeze(fields_params),
                as_thread,
            )
        if key is not None and key in cache:
            field_list, identifier = cache[key]
        else:
            # call _format_fields before checking identifier to always compare the final shape
            field_list = self._format_fields(fields, records, fields_params)
            identifier = Store._deep_freeze((records.env, records, field_list, as_thread))
            if key is not None:
                cache[key] = field_list, identifier
        if identifier in self.already_done:
            return self
        records_key = (records.env, records._name, records._ids, as_thread)
        running_field_lists = self.field_lists_in_progress[records_key]
        if running_field_lists:
            code_identifier = Store._deep_freeze(field_list, with_captures=False)
            if any(
                Store._deep_freeze(running, with_captures=False) == code_identifier
                for running in running_field_lists
            ):
                return self
        self.already_done.add(identifier)
        running_field_lists.append(field_list)
        self.add_depth += 1
        try:
            self._add_field_list(field_list, as_thread=as_thread, ignore_empty=ignore_empty)
            return self
        finally:
            running_field_lists.pop()
            self.add_depth -= 1
            if self.add_depth == 0:
                self.already_done.clear()
                self.field_lists_in_progress.clear()

    @store_enqueue
    def add_global_values(self, field_fn=None, /, **values):
        """Add global values to the store. Global values are stored in the Store singleton
        (mail.store service) in the client side.

        Use case: to add global values."""
        assert not field_fn or not values
        self.add_model_values("Store", field_fn or values)
        return self

    @store_enqueue
    def add_model_values(self, model_name, values, *, id_data=None, ignore_empty=False):
        """Add values to a model in the store.

        Use case: to add values to JS records that don't have a corresponding Python record.
        Note: for python records adding model values is discouraged in favor of using Store.add().
        """
        if not values:
            return self
        if isinstance(values, dict) and not any(map(callable, values.values())):
            data_list = [values]
        else:
            data_list = []
            self._add_abstract_fields_value(self._format_fields(values), data_list)
        index = self._get_record_index(model_name, [id_data or {}] + data_list)
        for data in data_list:
            self._add_values(data, model_name, index)
        has_data = any(
            key not in ("__version__", "__field_versions__") for key in self.data[model_name][index]
        )
        if id_data and (has_data or not ignore_empty):
            self._add_values(id_data, model_name, index)
        if "_DELETE" in self.data[model_name][index]:
            del self.data[model_name][index]["_DELETE"]
        return self

    def _add_field_list(self, field_list, *, as_thread=False, ignore_empty):
        """Add the given field list to the store, with its target blocks evaluated for the target
        of this store. This is an internal implementation method.
        In business code, Store.add() should be called instead.
        """
        records = field_list.records
        internal_blocks = []
        if any(isinstance(field, Store.TargetBlock) for field in field_list.data):
            fields, internal_blocks = self._resolve_target_blocks(records, field_list.data)
            field_list = Store.FieldList(records)
            field_list.extend(fields)
        if field_list and field_list.records:
            for record, record_data_list in self._get_records_data_list(
                field_list,
                ignore_empty=ignore_empty,
            ).items():
                for record_data in record_data_list:
                    model_name = record._name
                    id_data = {"id": record.id}
                    if as_thread:
                        model_name = "mail.thread"
                        id_data["model"] = record._name
                    self.add_model_values(
                        model_name,
                        record_data,
                        id_data=id_data,
                        ignore_empty=ignore_empty,
                    )
        if internal_blocks:
            internal_field_list = Store.FieldList(records)
            internal_field_list.extend(internal_blocks)
            self._internal_store._add_field_list(
                internal_field_list,
                as_thread=as_thread,
                ignore_empty=ignore_empty,
            )
        return self

    def _resolve_target_blocks(self, records, fields):
        """Return the given fields with their target blocks evaluated for the target of this
        store, and the blocks for internal users that go to its internal store."""
        resolved_fields = []
        internal_blocks = []

        def resolve(entries):
            for field in entries:
                if not isinstance(field, Store.TargetBlock):
                    resolved_fields.append(field)
                elif field.condition(self.target, records.env, *field.params):
                    resolve(Store._format_fields(field.fields, records).data)
                elif self._internal_store and field.condition(
                    self._internal_store.target,
                    records.env,
                    *field.params,
                ):
                    internal_blocks.append(field)

        resolve(fields)
        return resolved_fields, internal_blocks

    @store_enqueue
    def delete(self, records, as_thread=False):
        """Delete records from the store."""
        if not records:
            return self
        model_name = "mail.thread" if as_thread else records._name
        for record in records:
            values = (
                {"id": record.id} if not as_thread else {"id": record.id, "model": record._name}
            )
            index = self._get_record_index(model_name, [values])
            self._add_values(values, model_name, index)
            self.data[model_name][index]["_DELETE"] = True
        return self

    def get_client_action(self, next_action=None):
        """Gets client action to insert this store in the client."""
        return {
            "params": {
                "store_values": self,
                "next_action": next_action,
            },
            "tag": "mail.store_insert",
            "type": "ir.actions.client",
        }

    def as_dict(self):
        """Hook for JSON serialization used by the `json_default` method. Do not call
        directly. Returns a dictionary representing the aggregated result of all store
        commands, versioned.
        """
        return self._build_result(disable_auto_send=False)

    def _build_result(self, disable_auto_send=True):
        """Do not call directly. Executes pending operations and returns the aggregated
        result, automatically invoked by `as_dict()`."""
        if disable_auto_send:
            # Disable auto send, as the result was built manually. Assuming that the
            # caller doesn't want to send it.
            self._auto_send = False
            if self._internal_store:
                self._internal_store._auto_send = False
        self.is_executing_operation_queue = True
        try:
            for func in self.operation_queue:
                func()
            self.operation_queue.clear()
        finally:
            self.is_executing_operation_queue = False
        res = {}
        for model_name, records in sorted(self.data.items()):
            if not ids_by_model[model_name]:
                # singleton have a single item (the empty tuple), the wrapping list can be omitted
                res[model_name] = dict(sorted(records[()].items()))
            elif vals := [
                dict(sorted(record.items()))
                for record in records.values()
                if any(key not in ("__version__", "__field_versions__") for key in record)
            ]:
                # skip empty records and empty models
                res[model_name] = vals
        return res

    @store_enqueue
    def resolve_data_request(self, values=None, *, data_id=None):
        """Add values to the store for the current data request.

        Use case: resolve a specific data request from a client."""
        if not data_id:
            return self
        data_list = []
        self._add_abstract_fields_value(self._format_fields(values or [{}]), data_list)
        for data in data_list:
            self.add_model_values("DataResponse", {"id": data_id, "_resolve": True, **data})
        return self

    def _add_values(self, values: dict, model_name: str, index: tuple):
        """Adds values to the store for a given model name and index."""
        target = self.data[model_name][index]
        for key, val in values.items():
            assert key != "_DELETE", f"invalid key {key} in {model_name}: {values}"
            if key == "__field_versions__":
                target.setdefault("__field_versions__", {}).update(val)
            elif isinstance(val, Store.Relation):
                val._add_to_store(self, target, key)
            elif isinstance(val, datetime):
                target[key] = odoo.fields.Datetime.to_string(val)
            elif isinstance(val, date):
                target[key] = odoo.fields.Date.to_string(val)
            elif isinstance(val, Markup):
                target[key] = ["markup", str(val)]
            else:
                target[key] = val

    @staticmethod
    def _format_fields(fields, records=None, fields_params=None):
        field_list = Store.FieldList(records)
        if isinstance(fields, str) and (method := Store._get_fields_method(records, fields)):
            method(field_list, **(fields_params or {}))
        elif callable(fields):
            fields(field_list)
        elif isinstance(fields, dict):
            field_list.extend(Store.Attr(key, value) for key, value in fields.items())
        elif isinstance(fields, (list, tuple, Store.FieldList)):
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

    def _get_records_data_list(self, field_list, *, ignore_empty):
        abstract_fields = [field for field in field_list if isinstance(field, (dict, Store.Attr))]
        standard_fields = [f for f in field_list if f not in abstract_fields]
        records_data_list = {record: [] for record in field_list.records}
        if standard_fields or not ignore_empty:
            for record, data in zip(
                field_list.records,
                field_list.records._read_format(standard_fields, load=False),
            ):
                records_data_list[record].append(data)
        has_write_date = field_list.records and field_list.records._log_access
        unversioned = set()
        for record, record_data_list in records_data_list.items():
            self._add_abstract_fields_value(abstract_fields, record_data_list, record, unversioned)
            record_version = None
            if has_write_date:
                with suppress(MissingError):
                    # sudo: the record is sent, its write_date can be read
                    record_version = record.sudo().write_date
            # No write_date to version with: leave the field unversioned.
            if record_version:
                for record_data in record_data_list:
                    record_data["__version__"] = record_version.isoformat(timespec="microseconds")
                field_versions = {}
                for name in standard_fields:
                    if (
                        isinstance(name, str)
                        and (field := record._fields.get(name))
                        and not field.store
                    ):
                        version = Store._get_unstored_field_version(record, name)
                        if not version:
                            unversioned.add((record._name, name))
                        field_versions[name] = Store._format_version(version)
                if field_versions:
                    record_data_list.append({"__field_versions__": field_versions})
        for model_name, name in sorted(unversioned):
            Store._warn_unversioned(model_name, name)
        return records_data_list

    @staticmethod
    def _format_version(version):
        # None means unversioned: the value is applied whatever its arrival order.
        return version.isoformat(timespec="microseconds") if version else None

    @staticmethod
    def _warn_unversioned(model_name, field_name):
        _logger.warning(
            "Store: %s.%s has no reliable version and is sent unversioned. Pass an explicit "
            "version, or version=False if applying it in arrival order is fine.",
            model_name,
            field_name,
        )

    @staticmethod
    def _get_unstored_field_version(record, field_name, _seen=frozenset()):
        """Version of a field not stored on the record, whose write_date thus does not change
        with its value: the latest write_date among the records its value depends on.

        Only dependencies through stored many2one are followed, since writing any of them
        bumps the write_date of the record holding it. Returns None (unversioned) when the
        version could go backward or miss a change: dependencies through x2many (unlinking
        does not write the linked record), on the context, or none declared."""
        field = record._fields.get(field_name)
        registry = record.env.registry
        if (
            not field
            or field in _seen
            or not record._log_access
            or registry.field_depends_context[field]
            or not registry.field_depends[field]
        ):
            return None
        # sudo: dependencies are walked regardless of the access to the intermediate records.
        record = record.sudo()
        versions = []
        try:
            versions.append(record.write_date)
            for path in registry.field_depends[field]:
                records = record
                *hops, last = path.split(".")
                for hop in hops:
                    hop_field = records._fields[hop]
                    if hop_field.type != "many2one" or not hop_field.store:
                        return None
                    records = records[hop]
                    if not records:
                        break
                    if not records._log_access:
                        return None
                    versions.append(records.write_date)
                else:
                    # The last step is a plain field of `records`: a stored one is covered
                    # by the write_date of `records`, already collected above.
                    last_field = records._fields[last]
                    if last_field.type in ("one2many", "many2many"):
                        return None
                    if not last_field.store:
                        if not records:
                            continue
                        version = Store._get_unstored_field_version(
                            records,
                            last,
                            _seen | {field},
                        )
                        if not version:
                            return None
                        versions.append(version)
        except MissingError:
            return None
        return max(filter(None, versions), default=None)

    def _add_abstract_fields_value(self, abstract_fields, data_list, record=None, unversioned=None):
        for field in abstract_fields:
            try:
                if isinstance(field, dict):
                    data_list.append(field)
                elif not field.predicate or field.predicate(record):
                    data = {field.field_name: field._get_value(record)}
                    # A many's version is carried by its commands (see Many._get_id).
                    if (
                        not isinstance(field, Store.Many)
                        and field.field_name
                        and record is not None
                    ):
                        version = NO_VALUE
                        if field.version is not None:
                            version = field._get_version(record)
                        elif field._is_fake_field(record):
                            if field.value is NO_VALUE:
                                version = Store._get_unstored_field_version(
                                    record,
                                    field.field_name,
                                )
                            else:
                                version = None
                            if not version and record._log_access:
                                unversioned.add((record._name, field.field_name))
                        if version is not NO_VALUE:
                            data["__field_versions__"] = {
                                field.field_name: Store._format_version(version),
                            }
                    data_list.append(data)
            except MissingError:
                pass

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
        return record.id

    @staticmethod
    def _deep_freeze(obj, with_captures=True):
        """Recursively convert a data structure into an immutable version that can be hashed and
        compared for identity. Without captures, a function counts by its code only."""
        if obj is None or isinstance(obj, (str, int)):
            return obj
        if isinstance(obj, dict):
            return (
                "__dict__",
                frozenset(
                    (Store._deep_freeze(k, with_captures), Store._deep_freeze(v, with_captures))
                    for k, v in obj.items()
                ),
            )
        if isinstance(obj, list):
            return ("__list__", tuple(map(Store._deep_freeze, obj, repeat(with_captures))))
        if isinstance(obj, tuple):
            return tuple(map(Store._deep_freeze, obj, repeat(with_captures)))
        if isinstance(obj, set):
            return frozenset(map(Store._deep_freeze, obj, repeat(with_captures)))
        if isinstance(obj, (Store.Attr, Store.FieldList, Store.TargetBlock)):
            return Store._deep_freeze(obj._identity(), with_captures)
        if isinstance(obj, models.BaseModel):
            return ("__records__", obj.env, obj._name, obj._ids)
        if with_captures and isinstance(obj, MethodType):
            return Store._freeze_captured(obj)
        if hasattr(obj, "__code__"):
            captured = (
                (*(obj.__defaults__ or ()), *(obj.__closure__ or ())) if with_captures else ()
            )
            return ("__code__", hash(obj.__code__), tuple(map(Store._freeze_captured, captured)))
        return obj

    @staticmethod
    def _freeze_captured(value):
        if isinstance(value, CellType):
            try:
                value = value.cell_contents
            except ValueError:
                return Store.ObjectIdentity(value)
        if isinstance(value, models.BaseModel):
            return Store._deep_freeze(value)
        try:
            hash(value)
        except TypeError:
            return Store.ObjectIdentity(value)
        return value

    class ObjectIdentity:
        """Compares an unhashable value by object, keeping it alive so that its id is not reused."""

        def __init__(self, value):
            self.value = value

        def __eq__(self, other):
            return isinstance(other, Store.ObjectIdentity) and self.value is other.value

        def __hash__(self):
            return id(self.value)

    class LazyValue(Generic[T]):  # noqa: OLS01001
        def __init__(self, fn):
            """Helper to lazily compute a recordset, shared across multiple consumers
            (e.g., stores) while avoiding redundant queries.
            """
            self._fn = fn
            self._value = None

        def get(self, env) -> T:
            if self._value is None:
                self._value = self._fn()
            return self._value.with_env(env)

    class Stores(dict[object | tuple, "Store"]):
        """Lazy mapping to manage a list of Store indexed by bus target.
        Store methods are forwarded to all contained Store instances."""

        def __missing__(self, target):
            bus_channel, bus_subchannel = target if isinstance(target, tuple) else (target, None)
            return self.setdefault(target, Store(bus_channel, bus_subchannel))

        def __getattr__(self, name):
            if name not in {"add", "delete"}:
                raise AttributeError(f"'Stores' object has no attribute '{name}'")

            def stores_forward(*args, **kwargs):
                for store in self.values():
                    assert isinstance(store, Store)
                    # getattr: only allowed methods of Store are forwarded
                    getattr(store, name)(*args, **kwargs)

            return stores_forward

    class Target:
        """Target of the current store. Useful when information have to be added contextually
        depending on who is going to receive it."""

        def __init__(self, channel=None, subchannel=None):
            assert channel is None or isinstance(channel, models.Model), (
                f"channel should be None or a record: {channel}"
            )
            if channel is not None:
                channel = channel._bus_channels()
            assert channel is None or len(channel) <= 1, (
                f"channel should be empty or should be a single record: {channel}"
            )
            self.channel = channel
            self.subchannel = subchannel

        def is_for_current_user(self, env):
            """Return whether this target is the current user or guest of the given env.
            If there is no target at all, this is always True."""
            if self.channel is None and self.subchannel is None:
                return True
            user = self.target_user(env)
            guest = self.target_guest(env)
            return self.subchannel is None and (
                (user and user == env.user and not env.user._is_public())
                or (guest and guest == env["mail.guest"]._get_guest_from_context())
            )

        def is_for_group(self, env, group_xmlid):
            """Return whether this target implies the information will only be sent to users
            of the given group. If there is no target at all, the check is based on the current
            user of the env."""
            definitions = env["res.groups"]._get_group_definitions()
            group_id = definitions.get_id(group_xmlid)

            def implies_group(groups):
                return group_id in (*groups.ids, *definitions.get_superset_ids(groups.ids))

            bus_record = self.channel
            if bus_record is None and self.subchannel is None:
                bus_record = env.user
            return (
                (
                    isinstance(bus_record, env.registry["res.users"])
                    and self.subchannel is None
                    and bus_record._has_group(group_xmlid)
                )
                or (
                    isinstance(bus_record, env.registry["discuss.channel"])
                    and (
                        (
                            self.subchannel == "internal_users"
                            and implies_group(env.ref("base.group_user"))
                        )
                        or (
                            bus_record.channel_type == "channel"
                            and implies_group(bus_record.group_public_id)
                        )
                    )
                )
                or (
                    isinstance(bus_record, env.registry["res.groups"]) and implies_group(bus_record)
                )
            )

        def target_guest(self, env):
            """Return target guest (if any). Target guest is either this target if it is a
            guest, or the current guest from env if there is no target at all but there is a
            guest in the env.
            """
            records = self.channel
            if self.channel is None and self.subchannel is None:
                records = env["mail.guest"]._get_guest_from_context()
            return records if isinstance(records, env.registry["mail.guest"]) else env["mail.guest"]

        def target_user(self, env):
            """Return target user (if any). Target user is either this target if it is a user,
            or the current user from env if there is no target at all but there is a user in the
            env."""
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

        def __init__(
            self,
            field_name,
            value=NO_VALUE,
            *,
            predicate=None,
            sudo=False,
            version=None,
        ):
            self.field_name = field_name
            self.predicate = predicate
            self.sudo = sudo
            self.value = value
            self.version = version

        def _get_value(self, record):
            if self.value is NO_VALUE and record is not None and self.field_name in record._fields:
                return (record.sudo() if self.sudo else record)[self.field_name]
            if callable(self.value):
                if record is None:
                    return self.value()
                return self.value(record)
            if self.value is NO_VALUE:
                return None
            return self.value

        def _is_fake_field(self, record):
            """Whether the value does not come from a stored field of the record."""
            if self.value is not NO_VALUE:
                return True
            field = record._fields.get(self.field_name)
            return field is None or not field.store

        def _get_version(self, record):
            if callable(self.version):
                return self.version(record.sudo() if self.sudo else record)
            return self.version

        def _identity(self):
            return (
                self.__class__.__name__,
                self.field_name,
                self.predicate,
                self.sudo,
                self.value,
                self.version,
            )

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
            version=None,
        ):
            field_name = records_or_field_name if isinstance(records_or_field_name, str) else None
            super().__init__(
                field_name,
                predicate=predicate,
                sudo=sudo,
                value=value,
                version=version,
            )
            assert (
                not records_or_field_name
                or isinstance(records_or_field_name, (str, models.Model))
                or value is not NO_VALUE
            ), (
                f"expected recordset, field name, explicit value, or empty value for Relation: {records_or_field_name}"
            )
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
            # format fields early to ensure the final shape is used for identity whenever possible
            if self.records:
                self.fields = Store._format_fields(self.fields, self.records, self.fields_params)
                self.fields_params = None

        def _get_value(self, record):
            records = super()._get_value(record)
            if records is None and self.value is NO_VALUE:
                res_model_field = "res_model" if "res_model" in record._fields else "model"
                if self.field_name == "thread" and "thread" not in record._fields:
                    if (res_model := record[res_model_field]) and (res_id := record["res_id"]):
                        records = record.env[res_model].browse(res_id)
            return self._copy_with_records(records, calling_record=record)

        def _copy_with_records(self, records, calling_record):
            """Returns a new relation with the given records instead of the field name."""
            assert self.field_name and self.records is None
            assert not self.dynamic_fields or calling_record
            is_fake_field = self.value is not NO_VALUE and not isinstance(records, models.Model)
            if not is_fake_field and records:
                field_list = Store._format_fields(self.fields, records, self.fields_params)
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
                None if is_fake_field else records,
                field_list,
                as_thread=self.as_thread,
                fields_params=self.fields_params,
                only_data=self.only_data,
                value=records if is_fake_field else NO_VALUE,
            )

        def _add_to_store(self, store, target, key):
            """Add the current relation to the given store at target[key].

            Don't explicitly add the target records to the store if there are no
            fields to add for them to avoid top-level records with only ids.
            This prevents duplication as the ids are already sent through the
            relation itself if necessary."""
            store.add(self.records, self.fields, as_thread=self.as_thread, ignore_empty=True)

        def _identity(self):
            return (
                *super()._identity(),
                self.records.env if self.records else None,
                self.records,
                self.as_thread,
                self.dynamic_fields,
                self.fields,
                self.fields_params,
                self.only_data,
            )

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
            version=None,
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
                version=version,
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
            version=None,
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
                version=version,
            )
            self.mode = mode
            self.sort = sort
            # many2many has no FK column on either side: linking/unlinking never writes
            # the comodel record, so its write_date can't be trusted as the relation's
            # version. Only known when built from a named field.
            self._is_many2many = False
            # Not backed by a stored field: linking never writes the comodel record either.
            self._is_unstored = False

        def _copy_with_records(self, records, calling_record):
            if records is None:
                records = []
            res = super()._copy_with_records(records, calling_record)
            res.mode = self.mode
            res.sort = self.sort
            field = calling_record and calling_record._fields.get(self.field_name)
            res._is_many2many = field and field.type == "many2many"
            res._is_unstored = bool(calling_record) and (not field or not field.store)
            res.version = (
                self._get_version(calling_record)
                if calling_record is not None
                else self.version
            )
            if res.mode == "DELETE" and res.version is None and calling_record:
                res.version = calling_record.env.cr.now()
            if (
                res._is_unstored
                and res.mode == "ADD"
                and res.version is None
                and records
                and calling_record._log_access
            ):
                Store._warn_unversioned(calling_record._name, self.field_name)
            return res

        def _add_to_store(self, store: "Store", target, key):
            self._sort_records()
            super()._add_to_store(store, target, key)
            has_something_to_write = (
                self.value is not NO_VALUE or self.records or self.mode == "REPLACE"
            )
            if not self.only_data and has_something_to_write:
                rel_val = self._get_id()
                if self.mode == "REPLACE" or key not in target:
                    target[key] = rel_val
                    return
                if target[key] and not isinstance(target[key][0], tuple):
                    target[key] = [("REPLACE", target[key])]
                target[key] += rel_val

        def _get_id(self):
            """Return the ids that can be used to insert the current relation in the store."""
            if self.value is not NO_VALUE:
                res = self.value
            else:
                self._sort_records()
                res = [Store._get_one_id(record, self.as_thread) for record in self.records]
            if self.mode not in ("ADD", "DELETE") or self._is_many2many:
                # REPLACE/many2many are never versioned: their date can't be trusted.
                return self._prepend_mode(res)

            def stamp_version(val, write_date):
                version = write_date and write_date.isoformat(timespec="microseconds")
                if isinstance(val, dict):
                    return {**val, "__version__": version}
                return {"id": val, "__version__": version}

            values = res if isinstance(res, list) else [res]
            has_write_date = (
                self.value is NO_VALUE
                and self.mode == "ADD"
                and self.records
                and self.records._log_access
            )
            records = self.records if has_write_date else [None] * len(values)
            versioned = []
            for val, record in zip(values, records):
                version = self.version
                if version is None and record is not None:
                    if self._is_unstored:
                        # Linking does not write the comodel record: leave it unversioned.
                        versioned.append(val)
                        continue
                    with suppress(MissingError):
                        # sudo: the record is sent, its write_date can be read
                        version = record.sudo().write_date
                versioned.append(stamp_version(val, version) if version else val)
            return self._prepend_mode(versioned if isinstance(res, list) else versioned[0])

        def _prepend_mode(self, res):
            if self.mode == "ADD":
                res = [("ADD", res)]
            elif self.mode == "DELETE":
                res = [("DELETE", res)]
            return res

        def _sort_records(self):
            if self.sort:
                self.records = self.records.sorted(self.sort)
                self.sort = None

        def _identity(self):
            return (*super()._identity(), self.mode, self.sort)

    class FieldList(UserList):
        """Helper to provide short syntax for building a list of field definitions for a specific
        store.add call (with given records). Fields depending on the target go in
        for_current_user(), for_group() or for_internal_users(), whose conditions read the target
        of each store the list is added to."""

        def __init__(self, records):
            super().__init__()
            # records for which the field list will apply. Useful to pre-compute values in batch.
            self.records = records

        def __iter__(self):
            return iter(self.data)

        def __contains__(self, field):
            # Also match Store.Attr (not relations) by field name.
            return any(
                item == field
                or (
                    isinstance(item, Store.Attr)
                    and not isinstance(item, Store.Relation)
                    and item.field_name == field
                )
                for item in self
            )

        def attr(self, field_name, value=NO_VALUE, *, predicate=None, sudo=False, version=None):
            """Add an attribute to the field list."""
            if (
                self.records is not None
                and value is NO_VALUE
                and predicate is None
                and not sudo
                and version is None
            ):
                self.append(field_name)
            else:
                self.append(
                    Store.Attr(
                        field_name,
                        value=value,
                        predicate=predicate,
                        sudo=sudo,
                        version=version,
                    ),
                )

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

        def for_current_user(self, fields):
            """Add fields only when the target is the current user or guest, see
            Store.Target.is_for_current_user()."""
            self.append(Store.TargetBlock(fields, condition=Store.Target.is_for_current_user))

        def for_group(self, group_xmlid, fields):
            """Add fields only when the target implies the information will only be sent to
            users of the given group, see Store.Target.is_for_group(). For a channel target, the
            fields are sent to the internal users of the channel through its internal store when
            the group is implied by internal users."""
            self.append(
                Store.TargetBlock(
                    fields,
                    condition=Store.Target.is_for_group,
                    params=(group_xmlid,),
                ),
            )

        def for_internal_users(self, fields):
            """Add fields only for internal users, see for_group()."""
            self.for_group("base.group_user", fields)

        def _identity(self):
            return (self.__class__.__name__, self.records.env, self.records, tuple(self))

    class TargetBlock:
        """Fields depending on the target, evaluated for each store the field list is added to,
        when the target satisfies the given condition."""

        def __init__(self, fields, *, condition, params=()):
            self.condition = condition
            self.fields = fields
            self.params = params

        def _identity(self):
            return (self.__class__.__name__, self.condition, self.params, self.fields)

    class FieldListManager:
        """Similar API as Store.FieldList but for multiple field lists at once.
        This is necessary because each field list is added to a specific Store, and Store is tied
        to a specific (bus_channel, sub_channel), and there can be multiple bus_channel for one
        record depending on the result of _bus_channels()."""

        def __init__(self, stores, records, bus_target):
            """Initialize field lists by record for the given bus target.

            ``bus_target`` is expected in the following format:

            - single bus_subchannel (which can be ``None``), where bus_channel is implied as being
              the record on which it is called.
            - tuple of ``(field_name, bus_subchannel)``, where ``bus_channel`` is the record
              pointed by ``field_name`` on the record on which it is called
            """
            self._field_lists_by_record = {}
            if isinstance(bus_target, tuple):
                field_name, bus_subchannel = bus_target
            else:
                field_name, bus_subchannel = None, bus_target
            for record in records:
                target = record[field_name] if field_name else record
                self._field_lists_by_record[record] = [
                    (stores[bus_channel, bus_subchannel], Store.FieldList(record))
                    for bus_channel in target._bus_channels()
                ]

        def __getattr__(self, name):
            return partial(self._forward, name)

        def _forward(self, name, /, *args, **kwargs):
            if name not in {
                "attr",
                "extend",
                "for_current_user",
                "for_group",
                "for_internal_users",
                "from_method",
                "many",
                "one",
            }:
                raise AttributeError(
                    f"'FieldListManager' object has no attribute '{name}'",
                )
            for field_lists in self._field_lists_by_record.values():
                for _store, field_list in field_lists:
                    assert isinstance(field_list, Store.FieldList)
                    # getattr: only allowed methods of Store.FieldList are forwarded
                    getattr(field_list, name)(*args, **kwargs)

        def _resolve_target_blocks(self, record):
            """Replace the target blocks of the field lists of the given record by their fields
            for each store, the blocks for internal users going to the internal store. Done once,
            so that the values before and after a write are read for the same fields."""
            field_lists = self._field_lists_by_record[record]
            if not any(
                isinstance(field, Store.TargetBlock)
                for _store, field_list in field_lists
                for field in field_list.data
            ):
                return
            resolved_field_lists = []

            def add_resolved(store, fields):
                field_list = Store.FieldList(record)
                field_list.extend(fields)
                resolved_field_lists.append((store, field_list))

            for store, field_list in field_lists:
                fields, internal_blocks = store._resolve_target_blocks(record, field_list.data)
                add_resolved(store, fields)
                if internal_blocks:
                    internal_store = store._internal_store
                    add_resolved(
                        internal_store,
                        internal_store._resolve_target_blocks(record, internal_blocks)[0],
                    )
            self._field_lists_by_record[record] = resolved_field_lists

        @staticmethod
        def get_val_by_field_by_store_by_record(manager_list, records):
            """Given a list of Store.FieldListManager and records, returns a dict with all the
            values of the fields in the managers indexed by store and by record."""
            res = defaultdict(lambda: defaultdict(dict))
            for record, manager in product(records, manager_list):
                manager._resolve_target_blocks(record)
                for store, field_list in manager._field_lists_by_record[record]:
                    for field in field_list:
                        if isinstance(field, Store.Attr) and field.predicate and not field.predicate(record):
                            result = None
                        elif isinstance(field, Store.Relation):
                            result = field._get_value(record).records
                        elif isinstance(field, Store.Attr):
                            result = field._get_value(record)
                        else:
                            result = record[field]
                        res[record][store][field] = result
            return res
