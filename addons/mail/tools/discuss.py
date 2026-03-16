# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import math
import os
from collections import UserList, defaultdict
from datetime import date, datetime
from functools import partial, wraps
from itertools import product

from markupsafe import Markup

import odoo
from odoo import _, models
from odoo.exceptions import MissingError
from odoo.http import Response, request, route
from odoo.tools import OrderedSet, groupby

from odoo.addons.bus.websocket import wsrequest


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
        token = req.cookies.get(req.env["mail.guest"]._cookie_name, "")
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


class StoreVersionInternal:
    """Internal state used by the `@store_version` decorator."""
    def __init__(self):
        self._pending_bus_sends = []
        self._snapshot_data = None
        # Maps model names to record IDs to the set of updated field names.
        self._written_fields_by_record = defaultdict(lambda: defaultdict(OrderedSet))

    def enqueue_bus_notification(self, bus_channel, notification_type, payload):
        """Enqueue a bus notification to be sent when the `@store_version` decorator
        finishes, ensuring it includes the version metadata.
        """
        self._pending_bus_sends.append([bus_channel, notification_type, payload])

    def mark_field_as_written(self, model_name, record_ids, fname):
        """Mark field as written for the given records. Done automatically when using the
        ORM, should be done manually otherwise.
        """
        for id_ in record_ids:
            self._written_fields_by_record[model_name][id_].add(fname)

    def _get_formatted_version(self, env):
        """Get the version metadata, used by the client to determine if an incoming
        store insert is newer than what it already knows.
        """
        if not self._snapshot_data:
            env.flush_all()  # Ensure TX id is assigned, if the DB was modified, before building the version.
            env.cr.execute("SELECT pg_current_snapshot(), pg_current_xact_id_if_assigned()")
            snapshot_str, current_xact_id = env.cr.fetchone()
            xmin_str, xmax_str, xips_str = snapshot_str.split(":")
            xmin = int(xmin_str)
            xmax = int(xmax_str)
            xips = [int(x) for x in xips_str.split(",") if x]
            bitmap = bytearray(math.ceil((xmax - xmin) / 8))
            for x in xips:
                offset = x - xmin
                bitmap[offset // 8] |= 1 << (offset % 8)
            self._snapshot_data = {
                "xmin": str(xmin),
                "xmax": str(xmax),
                "xip_bitmap": base64.b64encode(bitmap).decode(),
                "current_xact_id": current_xact_id,
            }
        elif not self._snapshot_data["current_xact_id"]:
            env.flush_all()  # Ensure written fields are collected.
            if self._written_fields_by_record:
                # Snapshot was already fetched below in the stack, but fields have been
                # updated since then. The snapshot is frozen at the beginning of the TX,
                # but the current TX id is only assigned once the DB is modified. Update
                # it now.
                env.cr.execute("SELECT pg_current_xact_id_if_assigned()")
                self._snapshot_data["current_xact_id"] = env.cr.fetchone()[0]
        return {
            "snapshot": self._snapshot_data.copy(),
            "written_fields_by_record": {
                model: {record_id: list(fnames) for record_id, fnames in recs.items()}
                for model, recs in self._written_fields_by_record.items()
            },
        }

    def _inject_version(self, version, payload):
        """Add the version to the return value of `Store.get_result()`. Either the
        payload itself, or one of the values of the payload.
        """
        if isinstance(payload, Store.Result) and "__store_version__" not in payload:
            payload["__store_version__"] = version
            return True
        if isinstance(payload, dict):
            return any(self._inject_version(version, v) for v in payload.values())
        return False

    def _add_version_to_response(self, version, response):
        """Inject version metadata into the result returned by `Store.get_result()`,
        which may be either an HTTP response from a controller or a dict returned by the
        decorated function.
        """
        # Response is the result of `request.render()`, inject metadata inside the qweb context.
        if isinstance(response, Response) and response.template:
            self._inject_version(version, response.qcontext)
        else:
            self._inject_version(version, response)

    def _send_bus_notifications(self, env, version):
        """Send the notifications enqueued during the decorator method, alongside store
        version metadata.
        """
        for target, n_type, msg in self._pending_bus_sends:
            self._inject_version(version, msg)
            env["bus.bus"].with_context(mail_store=None)._sendone(target, n_type, msg)
        self._pending_bus_sends.clear()


def store_version(func):
    """Decorator to manage versioned updates in the store.

    Store data is received from RPC and from the bus, and is applied directly to the
    store. Without versioning, the order of arrival can cause outdated data to overwrite
    newer data, leading to incorrect store state.

    On the client side, we should be able to determine whether a field represents a newer
    version of what is already known. This is directly linked to PostgreSQL snapshots and
    isolation level, in our case, REPEATABLE READ.

    For fields that were read, what matters is what the snapshot could see at the time.
    For writes, what matters is whether the snapshot of the version we know could see the
    write transaction. The combination of xmin, xmax, xip and the current transaction id
    is enough to deduce it.

    This decorator injects version metadata into the return value of `Store.get_result()`,
    both in the value returned by the decorated function and in any bus notifications
    emitted during its execution.

    """
    @wraps(func)
    def store_version__wrapper(self, *args, **kwargs):
        manager = self.env.context.get("mail_store")
        should_cleanup = False
        if not manager:
            manager = StoreVersionInternal()
            if isinstance(self, models.BaseModel):
                self = self.with_context(mail_store=manager)
            else:
                # Clean up only if we inserted the manager in the request context;
                # otherwise, the original decorator will handle it.
                should_cleanup = True
                req = request or wsrequest
                req.update_context(mail_store=manager)
        response = func(self, *args, **kwargs)
        version = manager._get_formatted_version(self.env)
        manager._add_version_to_response(version, response)
        manager._send_bus_notifications(self.env, version)
        if should_cleanup:
            # Clean context to prevent side effects based on the presence of `mail_store`.
            req.update_context(mail_store=None)
        return response
    return store_version__wrapper


def mail_route(*route_args, **route_kwargs):
    """Thin wrapper around `route` that adds guest context and enables versioning.
    HTTP route results that return a non-Response object will automatically be converted
    into a proper HTTP JSON response using `request.make_json_response`.

    This decorator is equivalent to applying, in order:
        @route(*route_args, **route_kwargs)
        @store_version
        @add_guest_to_context
    """
    if "type" not in route_kwargs:
        raise TypeError(_("mail_route() must be called with the `type` keyword argument."))

    def decorator(func):
        wrapped_func = add_guest_to_context(func)
        wrapped_func = store_version(wrapped_func)

        @wraps(func)
        def mail_route__wrapper(*args, **kwargs):
            result = wrapped_func(*args, **kwargs)
            if route_kwargs["type"] == "http" and not isinstance(result, Response):
                return request.make_json_response(result)  # nosemgrep: rules.requests-in-models
            return result

        return route(*route_args, **route_kwargs)(mail_route__wrapper)

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


def store_enqueue(func):
    """Wraps a Store method to postpone its execution until get_result()."""

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
    It supports merging of data from multiple sources, either through list extend or dict update.
    The keys of data are the name of models as defined in mail JS code, and the values are any
    format supported by store.insert() method (single dict or list of dict for each model name)."""

    def __init__(self, bus_channel=None, bus_subchannel=None):
        self.add_depth = 0
        self.already_done = set()
        self.data = {}
        self.data_id = None
        self.is_executing_operation_queue = False
        self.operation_queue = []
        self.target = Store.Target(bus_channel, bus_subchannel)

    @store_enqueue
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
        # call _format_fields before checking identifier to always compare the final shape
        field_list = self._format_fields(fields, records, fields_params)
        identifier = Store._deep_freeze((records.env, records, field_list, as_thread))
        if identifier in self.already_done:
            return self
        self.already_done.add(identifier)
        self.add_depth += 1
        try:
            if not as_thread and hasattr(records, "_to_store"):
                records._to_store(self, field_list)
            else:
                self.add_records_fields(field_list, as_thread=as_thread)
            return self
        finally:
            self.add_depth -= 1
            if self.add_depth == 0:
                self.already_done.clear()

    @store_enqueue
    def add_global_values(self, field_fn=None, /, **values):
        """Add global values to the store. Global values are stored in the Store singleton
        (mail.store service) in the client side.

        Use case: to add global values."""
        assert not field_fn or not values
        self.add_singleton_values("Store", field_fn or values)
        return self

    @store_enqueue
    def add_model_values(self, model_name, values):
        """Add values to a model in the store.

        Use case: to add values to JS records that don't have a corresponding Python record.
        Note: for python records adding model values is discouraged in favor of using Store.add().
        """
        if not values:
            return self
        data_list = []
        self._add_abstract_fields_value(self._format_fields(values), data_list)
        index = self._get_record_index(model_name, data_list)
        self._ensure_record_at_index(model_name, index)
        for data in data_list:
            self._add_values(data, model_name, index)
        if "_DELETE" in self.data[model_name][index]:
            del self.data[model_name][index]["_DELETE"]
        return self

    @store_enqueue
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

    @store_enqueue
    def add_singleton_values(self, model_name, values):
        """Add values to the store for a singleton model."""
        if not values:
            return self
        data_list = []
        self._add_abstract_fields_value(self._format_fields(values), data_list)
        ids = ids_by_model[model_name]
        assert not ids
        if model_name not in self.data:
            self.data[model_name] = {}
        for data in data_list:
            self._add_values(data, model_name)
        return self

    @store_enqueue
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

    def get_client_action(self, next_action=None):
        """Gets client action to insert this store in the client."""
        return {
            "params": {
                "store_values": self.get_result(),
                "next_action": next_action,
            },
            "tag": "mail.store_insert",
            "type": "ir.actions.client",
        }

    def get_result(self):
        """Gets resulting data built from adding all data together."""
        self.is_executing_operation_queue = True
        try:
            for func in self.operation_queue:
                func()
            self.operation_queue.clear()
        finally:
            self.is_executing_operation_queue = False
        res = Store.Result()
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

    def _format_fields(self, fields, records=None, fields_params=None):
        field_list = Store.FieldList(self, records)
        if isinstance(fields, str) and (method := Store._get_fields_method(records, fields)):
            method(field_list, **(fields_params or {}))
        elif callable(fields):
            fields(field_list)
        elif isinstance(fields, dict):
            field_list.extend(Store.Attr(self, key, value) for key, value in fields.items())
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
                        {field.field_name: field._get_value(record)},
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
        return record.id

    @staticmethod
    def _deep_freeze(obj):
        """Recursively convert a data structure into an immutable version that can be hashed and
        compared for identity."""
        if isinstance(obj, (Store.FieldList, Store.Attr)):
            return Store._deep_freeze(obj._identity())
        if isinstance(obj, dict):
            return (
                "__dict__",
                frozenset((Store._deep_freeze(k), Store._deep_freeze(v)) for k, v in obj.items()),
            )
        if isinstance(obj, list):
            return ("__list__", tuple(Store._deep_freeze(i) for i in obj))
        if isinstance(obj, tuple):
            return tuple(Store._deep_freeze(i) for i in obj)
        if isinstance(obj, set):
            return frozenset(Store._deep_freeze(i) for i in obj)
        return obj

    class Stores(dict):
        """Lazy mapping to manage a list of Store indexed by bus target.
        Store methods are forwarded to all contained Store instances."""

        def __missing__(self, target):
            bus_channel, bus_subchannel = target if isinstance(target, tuple) else (target, None)
            return self.setdefault(target, Store(bus_channel, bus_subchannel))

        def __getattr__(self, name):
            if name not in {"add", "bus_send", "delete"}:
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

    class Result(dict):
        """Marker class for dictionaries returned by `Store.get_result()`.
        Used to distinguish store results from arbitrary dicts so version
        metadata can be added (see `store_version` decorator).
        """

    class Attr:
        """Attribute to be added for each record. The value can be a static value or a function
        to compute the value, receiving the record as argument.

        Use case: to add a value when it does not come directly from a field.
        Note: when a static value is given to a recordset, the same value is set on all records.
        """

        def __init__(self, store, field_name, value=NO_VALUE, *, predicate=None, sudo=False):
            self.store = store
            self.field_name = field_name
            self.predicate = predicate
            self.sudo = sudo
            self.value = value

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

        def _identity(self):
            return (
                self.__class__.__name__,
                self.field_name,
                self.predicate,
                self.sudo,
                self.value,
            )

    class Relation(Attr):
        """Flags a record or field name to be added to the store in a relation."""

        def __init__(
            self,
            store,
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
            super().__init__(store, field_name, predicate=predicate, sudo=sudo, value=value)
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
            # format fields early to ensure the final shape is used for identity whenever possible
            if self.records:
                self.fields = self.store._format_fields(self.fields, self.records, self.fields_params)
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
            if records:
                field_list = self.store._format_fields(self.fields, records, self.fields_params)
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
                self.store,
                records,
                field_list,
                as_thread=self.as_thread,
                fields_params=self.fields_params,
                only_data=self.only_data,
            )

        def _add_to_store(self, store, target, key):
            """Add the current relation to the given store at target[key]."""
            store.add(self.records, self.fields, as_thread=self.as_thread)

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
            store,
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
                store,
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
            store,
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
                store,
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

        def _copy_with_records(self, records, calling_record):
            if records is None:
                records = []
            res = super()._copy_with_records(records, calling_record)
            res.mode = self.mode
            res.sort = self.sort
            return res

        def _add_to_store(self, store: "Store", target, key):
            self._sort_records()
            super()._add_to_store(store, target, key)
            if not self.only_data and (self.records or self.mode == "REPLACE"):
                rel_val = self._get_id()
                if self.mode == "REPLACE" or key not in target:
                    target[key] = rel_val
                    return
                if target[key] and not isinstance(target[key][0], tuple):
                    target[key] = [("REPLACE", target[key])]
                target[key] += rel_val

        def _get_id(self):
            """Return the ids that can be used to insert the current relation in the store."""
            self._sort_records()
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

        def _sort_records(self):
            if self.sort:
                self.records = self.records.sorted(self.sort)
                self.sort = None

        def _identity(self):
            return (*super()._identity(), self.mode, self.sort)

    class FieldList(UserList):
        """Helper to provide short syntax for building a list of field definitions for a specific
        store.add call (with given records and target)."""
        def __init__(self, store, records):
            super().__init__()
            # records for which the field list will apply. Useful to pre-compute values in batch.
            self.records = records
            self.store = store

        @property
        def target(self):
            """Store.Target of the field list. Useful to adapt fields depending on the receivers."""
            return self.store.target

        def attr(self, field_name, value=NO_VALUE, *, predicate=None, sudo=False):
            """Add an attribute to the field list."""
            if self.records is not None and value is NO_VALUE and predicate is None and not sudo:
                self.append(field_name)
            else:
                self.append(
                    Store.Attr(self.store, field_name, value=value, predicate=predicate, sudo=sudo),
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
            self.append(Store.One(self.store, record_or_field_name, fields, *args, **kwargs))

        def many(self, records_or_field_name, fields, /, *args, **kwargs):
            """Add a x2many relation to the field list."""
            self.append(Store.Many(self.store, records_or_field_name, fields, *args, **kwargs))

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

        def _identity(self):
            return ("FieldList", self.records.env, self.records, tuple(self))

    class FieldListManager:
        """Similar API as Store.FieldList but for multiple field lists at once.
        This is necessary because FieldList is tied to a specific Store, and Store is tied
        to a specific (bus_channel, sub_channel), and there can be multiple bus_channel for one
        record depending on the result of _bus_channels()."""

        def __init__(self, stores, records, bus_target):
            """bus_target is expected in the following format:
            - single bus_subchannel (which can be None), where bus_channel is implied as being the
              record on which it is called.
            - tuple of (field_name, bus_subchannel), where bus_channel is the record pointed by
              field_name on the record on which it is called"""
            self._field_lists_by_record = {}
            if isinstance(bus_target, tuple):
                field_name, bus_subchannel = bus_target
            else:
                field_name, bus_subchannel = None, bus_target
            for record in records:
                target = record[field_name] if field_name else record
                self._field_lists_by_record[record] = [
                    Store.FieldList(stores[bus_channel, bus_subchannel], record)
                    for bus_channel in target._bus_channels()
                ]

        def __getattr__(self, name):
            return partial(self._forward, name)

        def _forward(self, name, /, *args, **kwargs):
            if name not in {"attr", "extend", "from_method", "many", "one"}:
                raise AttributeError(
                    f"'FieldListManager' object has no attribute '{name}'",
                )
            for field_lists in self._field_lists_by_record.values():
                for field_list in field_lists:
                    assert isinstance(field_list, Store.FieldList)
                    # getattr: only allowed methods of Store.FieldList are forwarded
                    getattr(field_list, name)(*args, **kwargs)

        @staticmethod
        def get_val_by_field_by_store_by_record(manager_list, records):
            """Given a list of Store.FieldListManager and records, returns a dict with all the
            values of the fields in the managers indexed by store and by record."""
            res = defaultdict(lambda: defaultdict(dict))
            for record, manager in product(records, manager_list):
                for field_list in manager._field_lists_by_record[record]:
                    for field in field_list:
                        if isinstance(field, Store.Attr) and field.predicate and not field.predicate(record):
                            result = None
                        elif isinstance(field, Store.Relation):
                            result = field._get_value(record).records
                        elif isinstance(field, Store.Attr):
                            result = field._get_value(record)
                        else:
                            result = record[field]
                        res[record][field_list.store][field] = result
            return res
