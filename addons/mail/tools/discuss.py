# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
from collections import defaultdict
from datetime import date, datetime

from odoo import fields, models
from odoo.tools import groupby


def get_twilio_credentials(env) -> (str, str):
    """
    To be overridable if we need to obtain credentials from another source.
    :return: tuple(account_sid: str, auth_token: str)
    """
    params = env["ir.config_parameter"].sudo()
    account_sid = params.get_param("mail.twilio_account_sid")
    auth_token = params.get_param("mail.twilio_account_token")
    return account_sid, auth_token


def get_sfu_url(env) -> str | None:
    sfu_url = env['ir.config_parameter'].sudo().get_param("mail.sfu_server_url")
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

    def __init__(
        self,
        data=None,
        values=None,
        /,
        *,
        fields=None,
        extra_fields=None,
        as_thread=False,
        delete=False,
        **kwargs,
    ):
        self.data = {}
        if data:
            self.add(
                data,
                values,
                fields=fields,
                extra_fields=extra_fields,
                as_thread=as_thread,
                delete=delete,
                **kwargs,
            )

    def add(
        self,
        data,
        values=None,
        /,
        *,
        fields=None,
        extra_fields=None,
        as_thread=False,
        delete=False,
        **kwargs,
    ):
        """Adds data to the store.
        - data can be a recordset, in which case the _to_store() method of the
          model will be called, with optional kwargs passed to it.
        - data can be a model name, in which case values must be a dict or list of dict.
        - data can be a dict, in which case it is considered as values for the Store model.
        - as_thread: whether to call "_thread_to_store" or "_to_store"
        - delete: whether to mark the record for deletion (client side)
        """
        if isinstance(data, models.Model):
            if values is not None:
                assert len(data) == 1, f"expected single record {data} with values: {values}"
                assert not kwargs, f"expected empty kwargs with recordset {data} values: {kwargs}"
                assert not delete, f"deleted not expected for {data} with values: {values}"
            if delete:
                assert len(data) == 1, f"expected single record {data} with delete"
                assert values is None, f"for {data} expected empty value with delete: {values}"
            if as_thread:
                if delete:
                    self.add("mail.thread", {"id": data.id, "model": data._name}, delete=True)
                elif values is not None:
                    self.add("mail.thread", {"id": data.id, "model": data._name, **values})
                else:
                    data._thread_to_store(self, fields=fields, **kwargs)
            else:
                if delete:
                    self.add(data._name, {"id": data.id}, delete=True)
                elif values is not None:
                    self.add(data._name, {"id": data.id, **values})
                else:
                    def add_fields(all_fields, new_fields):
                        for new_field in new_fields:
                            fname = (
                                new_field.field_name
                                if isinstance(new_field, (Store.One, Store.Many))
                                else new_field
                            )
                            all_fields = [
                                field
                                for field in all_fields
                                if (
                                    field.field_name != fname
                                    if isinstance(field, (Store.One, Store.Many))
                                    else field != fname
                                )
                            ] + [new_field]
                        return all_fields

                    all_fields = data._to_store_fields()
                    all_fields = add_fields(
                        all_fields,
                        fields if fields is not None else data._to_store_default_fields(),
                    )
                    if extra_fields:
                        all_fields = add_fields(all_fields, extra_fields)
                    data._to_store(self, fields=all_fields, **kwargs)
            return self
        if isinstance(data, dict):
            assert not values, f"expected empty values with dict {data}: {values}"
            assert not kwargs, f"expected empty kwargs with dict {data}: {kwargs}"
            assert not as_thread, f"expected not as_thread with dict {data}: {kwargs}"
            model_name = "Store"
            values = data
        else:
            assert not kwargs, f"expected empty kwargs with model name {data}: {kwargs}"
            assert not as_thread, f"expected not as_thread with model name {data}: {kwargs}"
            model_name = data
        assert isinstance(model_name, str), f"expected str for model name: {model_name}: {values}"
        # skip empty values
        if not values:
            return self
        ids = ids_by_model[model_name]
        # handle singleton model: update single record in place
        if not ids:
            assert isinstance(values, dict), f"expected dict for singleton {model_name}: {values}"
            assert not delete, f"Singleton {model_name} cannot be deleted"
            if model_name not in self.data:
                self.data[model_name] = {}
            self._add_values(values, model_name)
            return self
        # handle model with ids: add or update existing records based on ids
        if model_name not in self.data:
            self.data[model_name] = {}
        if isinstance(values, dict):
            values = [values]
        assert isinstance(values, list), f"expected list for {model_name}: {values}"
        for vals in values:
            assert isinstance(vals, dict), f"expected dict for {model_name}: {vals}"
            for i in ids:
                assert vals.get(i), f"missing id {i} in {model_name}: {vals}"
            index = tuple(vals[i] for i in ids)
            if index not in self.data[model_name]:
                self.data[model_name][index] = {}
            self._add_values(vals, model_name, index)
            if delete:
                self.data[model_name][index]["_DELETE"] = True
            elif "_DELETE" in self.data[model_name][index]:
                del self.data[model_name][index]["_DELETE"]
        return self

    def _add_values(self, values, model_name, index=None):
        """Adds values to the store for a given model name and index."""
        target = self.data[model_name][index] if index else self.data[model_name]
        for key, val in values.items():
            assert key != "_DELETE", f"invalid key {key} in {model_name}: {values}"
            if isinstance(val, Store.One):
                assert not val.record or isinstance(
                    val.record, models.Model
                ), f"expected recordset for one {key}: {val.record}"
                if val.record and not val.only_id:
                    self.add(val.record, as_thread=val.as_thread, **val.kwargs)
                target[key] = self.one_id(val.record, as_thread=val.as_thread)
            elif isinstance(val, Store.Many):
                assert not val.records or isinstance(
                    val.records, models.Model
                ), f"expected recordset for many {key}: {val.records}"
                assert val.mode in [
                    "ADD",
                    "DELETE",
                    "REPLACE",
                ], f"invalid mode for many {key}: {val.mode}"
                if val.records and not val.only_id:
                    self.add(val.records, as_thread=val.as_thread, **val.kwargs)
                rel_val = self.many_ids(val.records, val.mode, as_thread=val.as_thread)
                target[key] = (
                    target[key] + rel_val if key in target and val.mode != "REPLACE" else rel_val
                )
            elif isinstance(val, datetime):
                target[key] = fields.Datetime.to_string(val)
            elif isinstance(val, date):
                target[key] = fields.Date.to_string(val)
            else:
                target[key] = val

    def get_result(self):
        """Gets resulting data built from adding all data together."""
        res = {}
        for model_name, records in sorted(self.data.items()):
            if not ids_by_model[model_name]:  # singleton
                res[model_name] = dict(sorted(records.items()))
            else:
                res[model_name] = [dict(sorted(record.items())) for record in records.values()]
        return res

    @staticmethod
    def many_ids(records, mode="REPLACE", /, *, as_thread=False):
        """Converts records to a value suitable for a relation in the store.
        - mode: "REPLACE" (default), "ADD", or "DELETE".

        This method does not add the result to the Store. Calling it manually
        should be avoided. It is kept as a public method until all remaining
        occurences can be removed.
        Using the method ``many(..., only_id=True)`` is preferable."""
        if records._name == "mail.message.reaction":
            res = [
                {"message": message.id, "content": content}
                for (message, content), _ in groupby(records, lambda r: (r.message_id, r.content))
            ]
        else:
            res = [Store.one_id(record, as_thread=as_thread) for record in records]
        if mode == "ADD":
            res = [("ADD", res)]
        elif mode == "DELETE":
            res = [("DELETE", res)]
        return res

    @staticmethod
    def one_id(record, /, *, as_thread=False):
        """Converts a record to a value suitable for a relation in the store.

        This method does not add the result to the Store. Calling it manually
        should be avoided. It is kept as a public method until all remaining
        occurences can be removed.
        Using the method ``many(..., only_id=True)`` is preferable."""
        if not record:
            return False
        if as_thread:
            return {"id": record.id, "model": record._name}
        if record._name == "discuss.channel":
            return {"id": record.id, "model": "discuss.channel"}
        if record._name == "mail.guest":
            return {"id": record.id, "type": "guest"}
        if record._name == "res.partner":
            return {"id": record.id, "type": "partner"}
        return record.id

    class One:
        """Flags a record (or field name) to be added to the store in a One relation."""

        def __init__(self, record_or_field_name, /, as_thread=False, only_id=False, **kwargs):
            self.record = record_or_field_name
            self.field_name = record_or_field_name
            self.as_thread = as_thread
            self.only_id = only_id
            self.kwargs = kwargs

    class Many:
        """Flags records (or field name) to be added to the store in a Many relation.
        - mode: "REPLACE" (default), "ADD", or "DELETE"."""

        def __init__(
            self, records_or_field_name, mode="REPLACE", /, as_thread=False, only_id=False, **kwargs
        ):
            self.records = records_or_field_name
            self.field_name = records_or_field_name
            self.mode = mode
            self.as_thread = as_thread
            self.only_id = only_id
            self.kwargs = kwargs
