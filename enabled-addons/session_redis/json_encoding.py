# Copyright 2016-2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import json
from datetime import date, datetime

import dateutil


class SessionEncoder(json.JSONEncoder):
    """Encode date/datetime objects

    So that we can later recompose them if they were stored in the session
    """

    def default(self, obj):
        if isinstance(obj, datetime):
            return {"_type": "datetime_isoformat", "value": obj.isoformat()}
        elif isinstance(obj, date):
            return {"_type": "date_isoformat", "value": obj.isoformat()}
        elif isinstance(obj, set):
            return {"_type": "set", "value": tuple(obj)}
        return json.JSONEncoder.default(self, obj)


class SessionDecoder(json.JSONDecoder):
    """Decode json, recomposing recordsets and date/datetime"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, object_hook=self.object_hook, **kwargs)

    def object_hook(self, obj):
        if "_type" not in obj:
            return obj
        type_ = obj["_type"]
        if type_ == "datetime_isoformat":
            return dateutil.parser.parse(obj["value"])
        elif type_ == "date_isoformat":
            return dateutil.parser.parse(obj["value"]).date()
        elif type_ == "set":
            return set(obj["value"])
        return obj
