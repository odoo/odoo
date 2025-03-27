# copyright 2016 Camptocamp
# license lgpl-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

import json
from datetime import date, datetime

import dateutil
import lxml

from odoo import fields, models
from odoo.tools.func import lazy


class JobSerialized(fields.Field):
    """Provide the storage for job fields stored as json

    A base_type must be set, it must be dict, list or tuple.
    When the field is not set, the json will be the corresponding
    json string ("{}" or "[]").

    Support for some custom types has been added to the json decoder/encoder
    (see JobEncoder and JobDecoder).
    """

    type = "job_serialized"
    column_type = ("text", "text")

    _base_type = None

    # these are the default values when we convert an empty value
    _default_json_mapping = {
        dict: "{}",
        list: "[]",
        tuple: "[]",
        models.BaseModel: lambda env: json.dumps(
            {"_type": "odoo_recordset", "model": "base", "ids": [], "uid": env.uid}
        ),
    }

    def __init__(self, string=fields.Default, base_type=fields.Default, **kwargs):
        super().__init__(string=string, _base_type=base_type, **kwargs)

    def _setup_attrs(self, model, name):  # pylint: disable=missing-return
        super()._setup_attrs(model, name)
        if self._base_type not in self._default_json_mapping:
            raise ValueError("%s is not a supported base type" % (self._base_type))

    def _base_type_default_json(self, env):
        default_json = self._default_json_mapping.get(self._base_type)
        if not isinstance(default_json, str):
            default_json = default_json(env)
        return default_json

    def convert_to_column(self, value, record, values=None, validate=True):
        return self.convert_to_cache(value, record, validate=validate)

    def convert_to_cache(self, value, record, validate=True):
        # cache format: json.dumps(value) or None
        if isinstance(value, self._base_type):
            return json.dumps(value, cls=JobEncoder)
        else:
            return value or None

    def convert_to_record(self, value, record):
        default = self._base_type_default_json(record.env)
        return json.loads(value or default, cls=JobDecoder, env=record.env)


class JobEncoder(json.JSONEncoder):
    """Encode Odoo recordsets so that we can later recompose them"""

    def _get_record_context(self, obj):
        return obj._job_prepare_context_before_enqueue()

    def default(self, obj):
        if isinstance(obj, models.BaseModel):
            return {
                "_type": "odoo_recordset",
                "model": obj._name,
                "ids": obj.ids,
                "uid": obj.env.uid,
                "su": obj.env.su,
                "context": self._get_record_context(obj),
            }
        elif isinstance(obj, datetime):
            return {"_type": "datetime_isoformat", "value": obj.isoformat()}
        elif isinstance(obj, date):
            return {"_type": "date_isoformat", "value": obj.isoformat()}
        elif isinstance(obj, lxml.etree._Element):
            return {
                "_type": "etree_element",
                "value": lxml.etree.tostring(obj, encoding=str),
            }
        elif isinstance(obj, lazy):
            return obj._value
        return json.JSONEncoder.default(self, obj)


class JobDecoder(json.JSONDecoder):
    """Decode json, recomposing recordsets"""

    def __init__(self, *args, **kwargs):
        env = kwargs.pop("env")
        super().__init__(object_hook=self.object_hook, *args, **kwargs)
        assert env
        self.env = env

    def object_hook(self, obj):
        if "_type" not in obj:
            return obj
        type_ = obj["_type"]
        if type_ == "odoo_recordset":
            model = self.env(user=obj.get("uid"), su=obj.get("su"))[obj["model"]]
            if obj.get("context"):
                model = model.with_context(**obj.get("context"))
            return model.browse(obj["ids"])
        elif type_ == "datetime_isoformat":
            return dateutil.parser.parse(obj["value"])
        elif type_ == "date_isoformat":
            return dateutil.parser.parse(obj["value"]).date()
        elif type_ == "etree_element":
            return lxml.etree.fromstring(obj["value"])
        return obj
