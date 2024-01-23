# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
    if sfu_url:
        return sfu_url.rstrip("/")


def get_sfu_key(env) -> str | None:
    return env['ir.config_parameter'].sudo().get_param('mail.sfu_server_key')


class StoreData():
    """Helper to build a dict of data for sending to web client.
    It supports merging of data from multiple sources, either through list extend or dict update.
    The keys of data are the name of models as defined in mail JS code, and the values are any
    format supported by store.insert() method (single dict or list of dict for each model name)."""
    def __init__(self):
        self.data = {}

    def add(self, data):
        """Adds data to the store."""
        for key, val in data.items():
            if not val:
                continue
            if not isinstance(val, dict) and not isinstance(val, list):
                assert False, f"unsupported data type: {val}"
            if not key in self.data:
                self.data[key] = val
            else:
                if isinstance(val, list):
                    if not isinstance(self.data[key], list):
                        self.data[key] = [self.data[key]]
                    self.data[key].extend(val)
                elif isinstance(val, dict):
                    if isinstance(self.data[key], dict):
                        self.data[key].update(val)
                    else:
                        self.data[key].append(val)

    def get_result(self):
        """Gets resulting data built from adding all data together."""
        return self.data
