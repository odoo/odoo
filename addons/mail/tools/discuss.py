# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
from collections import defaultdict

from odoo import models


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
        "Persona": ("type", "id"),
        "Rtc": (),
        "Store": (),
        "Thread": ("model", "id"),
    }
)


class Store:
    """Helper to build a dict of data for sending to web client.
    It supports merging of data from multiple sources, either through list extend or dict update.
    The keys of data are the name of models as defined in mail JS code, and the values are any
    format supported by store.insert() method (single dict or list of dict for each model name)."""

    def __init__(self, data=None, values=None, /, **kwargs):
        self.data = {}
        if data:
            self.add(data, values, **kwargs)

    def add(self, data, values=None, /, **kwargs):
        """Adds data to the store.
        - data can be a recordset, in which case the model must have a _to_store() method, with
          optional kwargs passed to it.
        - data can be a model name, in which case values must be a dict or list of dict.
        - data can be a dict, in which case it is considered as values for the Store model.
        """
        if isinstance(data, models.Model):
            assert not values, f"expected empty values with recordset {data}: {values}"
            data._to_store(self, **kwargs)
            return self
        if isinstance(data, dict):
            assert not values, f"expected empty values with dict {data}: {values}"
            assert not kwargs, f"expected empty kwargs with dict {data}: {kwargs}"
            model_name = "Store"
            values = data
        else:
            assert not kwargs, f"expected empty kwargs with model name {data}: {kwargs}"
            model_name = data
        assert isinstance(model_name, str), f"expected str for model name: {model_name}: {values}"
        # skip empty values
        if not values:
            return self
        ids = ids_by_model[model_name]
        # handle singleton model: update single record in place
        if not ids:
            assert isinstance(values, dict), f"expected dict for singleton {model_name}: {values}"
            if model_name not in self.data:
                self.data[model_name] = {}
            self.data[model_name].update(values)
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
            if record := self.data[model_name].get(index):
                record.update(vals)
            else:
                self.data[model_name][index] = vals
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
