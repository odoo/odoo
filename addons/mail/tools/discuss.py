# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
from collections import defaultdict


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
        "Store": (),
        "Thread": ("model", "id"),
    }
)


class StoreData:
    """Helper to build a dict of data for sending to web client.
    It supports merging of data from multiple sources, either through list extend or dict update.
    The keys of data are the name of models as defined in mail JS code, and the values are any
    format supported by store.insert() method (single dict or list of dict for each model name)."""

    def __init__(self):
        self.data = {}

    def add(self, data):
        """Adds data to the store."""
        for key, vals in data.items():
            # skip empty values
            if not vals:
                continue
            ids = ids_by_model[key]
            # handle singleton: update in place
            if len(ids) == 0:
                if not isinstance(vals, dict):
                    assert False, f"expected dict for singleton {key}: {vals}"
                if not key in self.data:
                    self.data[key] = {}
                self.data[key].update(vals)
                continue
            # handle (multi) id(s): add or update existing
            if not key in self.data:
                self.data[key] = []
            if isinstance(vals, dict):
                vals = [vals]
            if not isinstance(vals, list):
                assert False, f"expected list for {key}: {vals}"
            for val in vals:
                if not isinstance(val, dict):
                    assert False, f"expected dict for {key}: {val}"
                for i in ids:
                    if not val.get(i):
                        assert False, f"missing key {i} in {key}: {val}"
                match = filter(lambda record: all(record[i] == val[i] for i in ids), self.data[key])
                if record := next(match, None):
                    record.update(val)
                else:
                    self.data[key].append(val)

    def get_result(self):
        """Gets resulting data built from adding all data together."""
        return self.data
