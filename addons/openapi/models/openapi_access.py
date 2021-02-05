# Copyright 2018-2019 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
# Copyright 2018 Rafis Bikbov <https://it-projects.info/team/bikbov>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
import collections
import inspect
import json
import types
import urllib.parse as urlparse
from inspect import getmro, isclass

from odoo import _, api, exceptions, fields, models

from odoo.addons.base_api.lib.pinguin import transform_strfields_to_dict

from ..controllers import pinguin

PARAM_ID = {
    "name": "id",
    "in": "path",
    "description": "Record ID",
    "required": True,
    "type": "integer",
    "format": "int64",
}


class Access(models.Model):
    _name = "openapi.access"
    _description = "Access via API "

    active = fields.Boolean("Active", default=True)
    namespace_id = fields.Many2one("openapi.namespace", "Integration", required=True)
    model_id = fields.Many2one("ir.model", "Model", required=True, ondelete='set_null   ')
    model = fields.Char("Model Name", related="model_id.model")
    api_create = fields.Boolean("Create via API", default=False)
    api_read = fields.Boolean("Read via API", default=False)
    api_update = fields.Boolean("Update via API", default=False)
    api_delete = fields.Boolean("Delete via API", default=False)
    # Options for Public methods:
    # * all forbidden
    # * all allowed
    # * some are allowed
    api_public_methods = fields.Boolean("Call Public methods via API", default=False,)
    public_methods = fields.Text(
        "Restric Public methods",
        help="Allowed public methods besides basic ones.\n"
        "Public methods are ones that don't start with underscore).\n"
        "Format: one method per line.\n"
        "When empty -- all public methods are allowed",
    )
    # Options for Private methods
    # * all forbidden
    # * some are allowed
    private_methods = fields.Text(
        "Allow Private methods",
        help="Allowed private methods. "
        "Private methods are ones that start with underscore. "
        "Format: one method per line. "
        "When empty -- private methods are not allowed",
    )
    read_one_id = fields.Many2one(
        "ir.exports",
        "Read One Fields",
        help="Fields to return on reading one record, on creating a record",
        domain="[('resource', '=', model)]",
    )
    read_many_id = fields.Many2one(
        "ir.exports",
        "Read Many Fields",
        help="Fields to return on reading via non one-record endpoint",
        domain="[('resource', '=', model)]",
    )
    create_context_ids = fields.Many2many(
        "openapi.access.create.context",
        string="Creation Context Presets",
        help="Can be used to pass default values or custom context",
        domain="[('model_id', '=', model_id)]",
    )

    _sql_constraints = [
        (
            "namespace_model_uniq",
            "unique (namespace_id, model_id)",
            "There is already a record for this Model",
        )
    ]

    @api.model
    def _get_method_list(self):
        return {
            m[0] for m in getmembers(self.env[self.model], predicate=inspect.ismethod)
        }

    @api.constrains("public_methods")
    def _check_public_methods(self):
        for access in self:
            if not access.public_methods:
                continue
            for line in access.public_methods.split("\n"):
                if not line:
                    continue
                if line.startswith("_"):
                    raise exceptions.ValidationError(
                        _(
                            'Private method (starting with "_" listed in public methods whitelist)'
                        )
                    )
                if line not in self._get_method_list():
                    raise exceptions.ValidationError(
                        _("Method %r is not part of the model's method list:\n %r")
                        % (line, self._get_method_list())
                    )

    @api.constrains("private_methods")
    def _check_private_methods(self):
        for access in self:
            if not access.private_methods:
                continue
            for line in access.private_methods.split("\n"):
                if not line:
                    continue
                if not line.startswith("_"):
                    raise exceptions.ValidationError(
                        _(
                            'Public method (not starting with "_" listed in private methods whitelist'
                        )
                    )
                if line not in self._get_method_list():
                    raise exceptions.ValidationError(
                        _("Method %r is not part of the model's method list:\n %r")
                        % (line, self._get_method_list())
                    )

    @api.constrains("api_create", "api_read", "api_update", "api_delete")
    def _check_methods(self):
        for record in self:
            methods = [
                record.api_create,
                record.api_read,
                record.api_update,
                record.api_delete,
                record.api_public_methods,
            ]
            methods += (record.public_methods or "").split("\n")
            methods += (record.private_methods or "").split("\n")
            if all(not m for m in methods):
                raise exceptions.ValidationError(
                    _('You must select at least one API method for "%s" model.')
                    % record.model
                )

    def name_get(self):
        return [
            (record.id, "{}/{}".format(record.namespace_id.name, record.model))
            for record in self
        ]

    def get_OAS_paths_part(self):
        model_name = self.model
        read_many_path = "/%s" % model_name
        read_one_path = "%s/{id}" % read_many_path
        patch_one_path = read_one_path + "/call/{method_name}"
        patch_model_path = read_many_path + "/call/{method_name}"
        patch_many_path = read_many_path + "/call/{method_name}/{ids}"

        read_many_definition_ref = "#/definitions/%s" % pinguin.get_definition_name(
            self.model, "", "read_many"
        )
        read_one_definition_ref = "#/definitions/%s" % pinguin.get_definition_name(
            self.model, "", "read_one"
        )
        patch_definition_ref = "#/definitions/%s" % pinguin.get_definition_name(
            self.model, "", "patch"
        )

        capitalized_model_name = "".join(
            [s.capitalize() for s in model_name.split(".")]
        )

        paths_object = collections.OrderedDict(
            [
                (read_many_path, {}),
                (read_one_path, {}),
                (patch_model_path, {}),
                (patch_many_path, {}),
                (patch_one_path, {}),
            ]
        )

        if self.api_create:
            paths_object[read_many_path]["post"] = {
                "summary": "Add a new %s object to the store" % model_name,
                "description": "",
                "operationId": "add%s" % capitalized_model_name,
                "consumes": ["application/json"],
                "parameters": [
                    {
                        "in": "body",
                        "name": "body",
                        "description": "%s object that needs to be added to the store"
                        % model_name,
                        "required": True,
                        "schema": {
                            "$ref": "#/definitions/%s"
                            % pinguin.get_definition_name(self.model)
                        },
                    }
                ],
                "responses": {
                    "201": {
                        "description": "successful create",
                        "schema": {"$ref": "#/definitions/%s-read_one" % model_name},
                    },
                },
            }

        if self.api_read:
            paths_object[read_many_path]["get"] = {
                "summary": "Get all %s objects" % model_name,
                "description": "Returns all %s objects" % model_name,
                "operationId": "getAll%s" % capitalized_model_name,
                "produces": ["application/json"],
                "responses": {
                    "200": {
                        "description": "A list of %s." % model_name,
                        "schema": {
                            "type": "array",
                            "items": {"$ref": read_many_definition_ref},
                        },
                    }
                },
            }

            paths_object[read_one_path]["get"] = {
                "summary": "Get %s by ID" % model_name,
                "description": "Returns a single %s" % model_name,
                "operationId": "get%sById" % capitalized_model_name,
                "produces": ["application/json"],
                "parameters": [PARAM_ID],
                "responses": {
                    "200": {
                        "description": "successful operation",
                        "schema": {"$ref": read_one_definition_ref},
                    },
                    "404": {"description": "%s not found" % model_name},
                },
            }

        if self.api_update:
            paths_object[read_one_path]["put"] = {
                "summary": "Update %s by ID" % model_name,
                "description": "",
                "operationId": "update%sById" % capitalized_model_name,
                "parameters": [
                    PARAM_ID,
                    {
                        "in": "body",
                        "name": "body",
                        "description": "Updated %s object" % model_name,
                        "required": True,
                        "schema": {
                            "$ref": "#/definitions/%s"
                            % pinguin.get_definition_name(self.model)
                        },
                    },
                ],
                "responses": {
                    "204": {"description": "successful update"},
                    "404": {"description": "%s not found" % model_name},
                },
            }

        if self.api_delete:
            paths_object[read_one_path]["delete"] = {
                "summary": "Delete %s by ID" % model_name,
                "description": "",
                "operationId": "delete%s" % capitalized_model_name,
                "produces": ["application/json"],
                "parameters": [PARAM_ID],
                "responses": {
                    "204": {"description": "successful delete"},
                    "404": {"description": "%s not found" % model_name},
                },
            }

        if self.api_public_methods or self.public_methods or self.private_methods:
            allowed_methods = []
            if self.api_public_methods:
                allowed_methods += [
                    m for m in self._get_method_list() if not m.startswith("_")
                ]
            elif self.public_methods:
                allowed_methods += [m for m in self.public_methods.split("\n") if m]
            if self.private_methods:
                allowed_methods += [m for m in self.private_methods.split("\n") if m]

            allowed_methods = list(set(allowed_methods))

            PARAM_METHOD_NAME = {
                "name": "method_name",
                "in": "path",
                "description": "Method Name",
                "required": True,
                "type": "string",
                "enum": allowed_methods,
            }
            PARAM_BODY = {
                "in": "body",
                "name": "body",
                "description": "Parameters for calling the method on a recordset",
                "schema": {"$ref": patch_definition_ref},
            }
            RESPONSES = {
                "200": {"description": "successful patch"},
                "403": {
                    "description": "Requested model method is not allowed",
                    "schema": {"$ref": "#/definitions/ErrorResponse"},
                },
            }

            paths_object[patch_one_path]["patch"] = {
                "summary": "Patch %s by single ID" % model_name,
                "description": "Call model method for single record.",
                "operationId": "callMethodFor%sSingleRecord" % capitalized_model_name,
                "consumes": ["application/json"],
                "produces": ["application/json"],
                "parameters": [PARAM_ID, PARAM_METHOD_NAME, PARAM_BODY],
                "responses": RESPONSES,
            }

            paths_object[patch_model_path]["patch"] = {
                "summary": "Patch %s" % model_name,
                "description": "Call model method on model",
                "operationId": "callMethodFor%sModel" % capitalized_model_name,
                "consumes": ["application/json"],
                "produces": ["application/json"],
                "parameters": [PARAM_METHOD_NAME, PARAM_BODY],
                "responses": RESPONSES,
            }

            paths_object[patch_many_path]["patch"] = {
                "summary": "Patch %s by some IDs" % model_name,
                "description": "Call model method for recordset.",
                "operationId": "callMethodFor%sRecordset" % capitalized_model_name,
                "consumes": ["application/json"],
                "produces": ["application/json"],
                "parameters": [
                    {
                        "name": "ids",
                        "in": "path",
                        "description": "Comma-separated Record IDS",
                        "required": True,
                        "type": "string",
                    },
                    PARAM_METHOD_NAME,
                    PARAM_BODY,
                ],
                "responses": RESPONSES,
            }

        paths_object = {k: v for k, v in paths_object.items() if v}
        for _path_item_key, path_item_value in paths_object.items():

            for path_method in path_item_value.values():
                # add tag
                path_method.update({"tags": [model_name]})

                # add global responses
                path_method["responses"].update(
                    {
                        400: {"$ref": "#/responses/400"},
                        401: {"$ref": "#/responses/401"},
                        500: {"$ref": "#/responses/500"},
                    }
                )

        return paths_object

    def get_OAS_definitions_part(self):
        related_model = self.env[self.model]
        export_fields_read_one = transform_strfields_to_dict(
            self.read_one_id.export_fields.mapped("name") or ("id",)
        )
        export_fields_read_many = transform_strfields_to_dict(
            self.read_many_id.export_fields.mapped("name") or ("id",)
        )
        definitions = {}
        definitions.update(
            pinguin.get_OAS_definitions_part(
                related_model, export_fields_read_one, definition_postfix="read_one"
            )
        )
        definitions.update(
            pinguin.get_OAS_definitions_part(
                related_model, export_fields_read_many, definition_postfix="read_many"
            )
        )
        if self.api_create or self.api_update:
            all_fields = transform_strfields_to_dict(related_model.fields_get_keys())
            definitions.update(
                pinguin.get_OAS_definitions_part(related_model, all_fields)
            )

        if self.api_public_methods or self.private_methods:
            definitions.update(
                {
                    pinguin.get_definition_name(self.model, "", "patch"): {
                        "type": "object",
                        "example": {
                            "args": [],
                            "kwargs": {
                                "body": "Message is posted via API by calling message_post method",
                                "subject": "Test API",
                            },
                            "context": {},
                        },
                    }
                }
            )
        return definitions

    def get_OAS_part(self):
        self = self.sudo()
        return {
            "definitions": self.get_OAS_definitions_part(),
            "paths": self.get_OAS_paths_part(),
            "tag": {
                "name": "%s" % self.model,
                "description": "Everything about %s" % self.model,
            },
        }


class AccessCreateContext(models.Model):
    _name = "openapi.access.create.context"
    _description = "Context on creating via API "

    name = fields.Char("Name", required=True)
    description = fields.Char("Description")
    model_id = fields.Many2one("ir.model", "Model", required=True)
    context = fields.Text("Context", required=True)

    _sql_constraints = [
        (
            "context_model_name_uniq",
            "unique (name, model_id)",
            "There is already a context with the same name for this Model",
        )
    ]

    @api.model
    def _fix_name(self, vals):
        if "name" in vals:
            vals["name"] = urlparse.quote_plus(vals["name"].lower())
        return vals

    @api.model
    def create(self, vals):
        vals = self._fix_name(vals)
        return super(AccessCreateContext, self).create(vals)

    def write(self, vals):
        vals = self._fix_name(vals)
        return super(AccessCreateContext, self).write(vals)

    @api.constrains("context")
    def _check_context(self):
        Model = self.env[self.model_id.model]
        fields = Model.fields_get()
        for record in self:
            try:
                data = json.loads(record.context)
            except ValueError:
                raise exceptions.ValidationError(_("Context must be jsonable."))

            for k, _v in data.items():
                if k.startswith("default_") and k[8:] not in fields:
                    raise exceptions.ValidationError(
                        _('The model "%s" has no such field: "%s".') % (Model, k[8:])
                    )


def getmembers(obj, predicate=None):
    # This is copy-pasted method from inspect lib with updates marked as NEW
    """Return all members of an object as (name, value) pairs sorted by name.
    Optionally, only return members that satisfy a given predicate."""
    if isclass(obj):
        mro = (obj,) + getmro(obj)
    else:
        mro = ()
    results = []
    processed = set()
    names = dir(obj)
    # :dd any DynamicClassAttributes to the list of names if object is a class;
    # this may result in duplicate entries if, for example, a virtual
    # attribute with the same name as a DynamicClassAttribute exists
    try:
        for base in obj.__bases__:
            for k, v in base.__dict__.items():
                if isinstance(v, types.DynamicClassAttribute):
                    names.append(k)
    except AttributeError:
        pass
    for key in names:
        if key == "_cache":
            # NEW
            # trying to read this key will return error in odoo 11.0+
            # AssertionError: Unexpected RecordCache(res.partner())
            continue
        # First try to get the value via getattr.  Some descriptors don't
        # like calling their __get__ (see bug #1785), so fall back to
        # looking in the __dict__.
        try:
            value = getattr(obj, key)
            # handle the duplicate key
            if key in processed:
                raise AttributeError
        except AttributeError:
            for base in mro:
                if key in base.__dict__:
                    value = base.__dict__[key]
                    break
            else:
                # could be a (currently) missing slot member, or a buggy
                # __dir__; discard and move on
                continue
        if not predicate or predicate(value):
            results.append((key, value))
        processed.add(key)
    results.sort(key=lambda pair: pair[0])
    return results
