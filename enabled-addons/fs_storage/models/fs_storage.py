# Copyright 2023 ACSONE SA/NV (https://www.acsone.eu).
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from __future__ import annotations

import base64
import functools
import inspect
import json
import logging
import os.path
import re
import warnings
from typing import AnyStr

import fsspec

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError

from odoo.fields import Json

_logger = logging.getLogger(__name__)

LS_NON_EXISTING_FILE = ".NON_EXISTING_FILE"


# TODO: useful for the whole OCA?
def deprecated(reason):
    """Mark functions or classes as deprecated.

    Emit warning at execution.

    The @deprecated is used with a 'reason'.

        .. code-block:: python

            @deprecated("please, use another function")
            def old_function(x, y):
                pass
    """

    def decorator(func1):
        if inspect.isclass(func1):
            fmt1 = "Call to deprecated class {name} ({reason})."
        else:
            fmt1 = "Call to deprecated function {name} ({reason})."

        @functools.wraps(func1)
        def new_func1(*args, **kwargs):
            warnings.simplefilter("always", DeprecationWarning)
            warnings.warn(
                fmt1.format(name=func1.__name__, reason=reason),
                category=DeprecationWarning,
                stacklevel=2,
            )
            warnings.simplefilter("default", DeprecationWarning)
            return func1(*args, **kwargs)

        return new_func1

    return decorator


class FSStorage(models.Model):
    _name = "fs.storage"
    _inherit = "server.env.mixin"
    _description = "FS Storage"

    __slots__ = ("__fs", "__odoo_storage_path")

    def __init__(self, env, ids=(), prefetch_ids=()):
        super().__init__(env, ids=ids, prefetch_ids=prefetch_ids)
        self.__fs = None
        self.__odoo_storage_path = None

    name = fields.Char(required=True)
    code = fields.Char(
        required=True,
        help="Technical code used to identify the storage backend into the code."
        "This code must be unique. This code is used for example to define the "
        "storage backend to store the attachments via the configuration parameter "
        "'ir_attachment.storage.force.database' when the module 'fs_attachment' "
        "is installed.",
    )
    protocol = fields.Selection(
        selection="_get_protocols",
        required=True,
        help="The protocol used to access the content of filesystem.\n"
        "This list is the one supported by the fsspec library (see "
        "https://filesystem-spec.readthedocs.io/en/latest). A filesystem protocol"
        "is added by default and refers to the odoo local filesystem.\n"
        "Pay attention that according to the protocol, some options must be"
        "provided through the options field.",
    )
    protocol_descr = fields.Text(
        compute="_compute_protocol_descr",
    )
    options = fields.Text(
        help="The options used to initialize the filesystem.\n"
        "This is a JSON field that depends on the protocol used.\n"
        "For example, for the sftp protocol, you can provide the following:\n"
        "{\n"
        "    'host': 'my.sftp.server',\n"
        "    'ssh_kwrags': {\n"
        "        'username': 'myuser',\n"
        "        'password': 'mypassword',\n"
        "        'port': 22,\n"
        "    }\n"
        "}\n"
        "For more information, please refer to the fsspec documentation:\n"
        "https://filesystem-spec.readthedocs.io/en/latest/api.html#built-in-implementations"
    )

    json_options = Json(
        help="The options used to initialize the filesystem.\n",
        compute="_compute_json_options",
        inverse="_inverse_json_options",
    )

    eval_options_from_env = fields.Boolean(
        string="Resolve env vars",
        help="""Resolve options values starting with $ from environment variables. e.g
            {
                "endpoint_url": "$AWS_ENDPOINT_URL",
            }
            """,
    )

    # When accessing this field, use the method get_directory_path instead so that
    # parameter expansion is done.
    directory_path = fields.Char(
        help="Relative path to the directory to store the file",
    )

    model_xmlids = fields.Char(
        help="List of models xml ids such as attachments linked to one of "
        "these models will be stored in this storage."
    )
    model_ids = fields.One2many(
        "ir.model",
        "storage_id",
        help="List of models such as attachments linked to one of these "
        "models will be stored in this storage.",
        compute="_compute_model_ids",
        inverse="_inverse_model_ids",
    )
    field_xmlids = fields.Char(
        help="List of fields xml ids such as attachments linked to one of "
        "these fields will be stored in this storage. NB: If the attachment "
        "is linked to a field that is in one FS storage, and the related "
        "model is in another FS storage, we will store it into"
        " the storage linked to the resource field."
    )
    field_ids = fields.One2many(
        "ir.model.fields",
        "storage_id",
        help="List of fields such as attachments linked to one of these "
        "fields will be stored in this storage. NB: If the attachment "
        "is linked to a field that is in one FS storage, and the related "
        "model is in another FS storage, we will store it into"
        " the storage linked to the resource field.",
        compute="_compute_field_ids",
        inverse="_inverse_field_ids",
    )

    # the next fields are used to display documentation to help the user
    # to configure the backend
    options_protocol = fields.Selection(
        string="Describes Protocol",
        selection="_get_options_protocol",
        compute="_compute_protocol_descr",
        help="The protocol used to access the content of filesystem.\n"
        "This list is the one supported by the fsspec library (see "
        "https://filesystem-spec.readthedocs.io/en/latest). A filesystem protocol"
        "is added by default and refers to the odoo local filesystem.\n"
        "Pay attention that according to the protocol, some options must be"
        "provided through the options field.",
    )
    options_properties = fields.Text(
        string="Available properties",
        compute="_compute_options_properties",
        store=False,
    )
    check_connection_method = fields.Selection(
        selection="_get_check_connection_method_selection",
        default="marker_file",
        help="Set a method if you want the connection to remote to be checked every "
        "time the storage is used, in order to remove the obsolete connection from"
        " the cache.\n"
        "* Create Marker file : Create a file on remote and check it exists\n"
        "* List File : List all files from root directory",
    )

    is_cacheable = fields.Boolean(
        help="If True, once instantiated, the filesystem will be cached and reused.\n"
        "By default, the filesystem is cacheable but in some cases, like "
        "when using OAuth2 authentication, the filesystem cannot be cached "
        "because it depends on the user and the token can change.\n"
        "In this case, you can set this field to False to avoid caching the "
        "filesystem.",
        default=True,
    )

    _sql_constraints = [
        (
            "code_uniq",
            "unique(code)",
            "The code must be unique",
        ),
    ]

    _server_env_section_name_field = "code"

    @api.constrains("model_xmlids")
    def _check_model_xmlid_storage_unique(self):
        """
        A given model can be stored in only 1 storage.
        As model_ids is a non stored field, we must implement a Python
        constraint on the XML ids list.
        """
        for rec in self.filtered("model_xmlids"):
            xmlids = rec.model_xmlids.split(",")
            for xmlid in xmlids:
                other_storages = (
                    self.env["fs.storage"]
                    .search([])
                    .filtered_domain(
                        [
                            ("id", "!=", rec.id),
                            ("model_xmlids", "ilike", xmlid),
                        ]
                    )
                )
                if other_storages:
                    raise ValidationError(
                        _(
                            "Model %(model)s already stored in another "
                            "FS storage ('%(other_storage)s')"
                        )
                        % {"model": xmlid, "other_storage": other_storages[0].name}
                    )

    @api.constrains("field_xmlids")
    def _check_field_xmlid_storage_unique(self):
        """
        A given field can be stored in only 1 storage.
        As field_ids is a non stored field, we must implement a Python
        constraint on the XML ids list.
        """
        for rec in self.filtered("field_xmlids"):
            xmlids = rec.field_xmlids.split(",")
            for xmlid in xmlids:
                other_storages = (
                    self.env["fs.storage"]
                    .search([])
                    .filtered_domain(
                        [
                            ("id", "!=", rec.id),
                            ("field_xmlids", "ilike", xmlid),
                        ]
                    )
                )
                if other_storages:
                    raise ValidationError(
                        _(
                            "Field %(field)s already stored in another "
                            "FS storage ('%(other_storage)s')"
                        )
                        % {"field": xmlid, "other_storage": other_storages[0].name}
                    )

    @api.model
    def _get_check_connection_method_selection(self):
        return [
            ("marker_file", _("Create Marker file")),
            ("ls", _("List File")),
        ]

    @property
    def _server_env_fields(self):
        return {
            "protocol": {},
            "options": {},
            "directory_path": {},
            "eval_options_from_env": {},
            "model_xmlids": {},
            "field_xmlids": {},
            "check_connection_method": {},
        }

    def write(self, vals):
        self.__fs = None
        self.env.registry.clear_cache()
        return super().write(vals)

    def get_directory_path(self):
        """Returns directory path with substitution done."""
        return (
            self.directory_path.format(db_name=self.env.cr.dbname)
            if isinstance(self.directory_path, str)
            else self.directory_path
        )

    @api.model
    @tools.ormcache()
    def get_id_by_code_map(self):
        """Return a dictionary with the code as key and the id as value."""
        return {rec.code: rec.id for rec in self.sudo().search([])}

    @api.model
    def get_id_by_code(self, code):
        """Return the id of the filesystem associated to the given code."""
        return self.get_id_by_code_map().get(code)

    @api.model
    def get_by_code(self, code) -> FSStorage:
        """Return the filesystem associated to the given code."""
        res = self.browse()
        res_id = self.get_id_by_code(code)
        if res_id:
            res = self.browse(res_id)
        return res

    @api.model
    @tools.ormcache("code")
    def get_protocol_by_code(self, code):
        record = self.get_by_code(code)
        return record.protocol if record else None

    @api.model
    @tools.ormcache("code")
    def _is_fs_cacheable(self, code):
        """Return True if the filesystem is cacheable."""
        # This method is used to check if the filesystem is cacheable.
        # It is used to avoid caching filesystems that are not cacheable.
        # For example, the msgd protocol is not cacheable because it uses
        # OAuth2 authentication and the token can change.
        fs_storage = self.get_by_code(code)
        return fs_storage and fs_storage.is_cacheable

    @api.model
    @tools.ormcache()
    def get_storage_codes(self):
        """Return the list of codes of the existing filesystems."""
        return [s.code for s in self.search([])]

    @api.model
    @tools.ormcache("code")
    def _get_fs_by_code_from_cache(self, code):
        return self.get_fs_by_code(code, force_no_cache=True)

    @api.model
    def get_fs_by_code(self, code, force_no_cache=False):
        """Return the filesystem associated to the given code.

        :param code: the code of the filesystem
        """

        use_cache = not force_no_cache and self._is_fs_cacheable(code)
        fs = None
        if use_cache:
            fs = self._get_fs_by_code_from_cache(code)
        else:
            fs_storage = self.get_by_code(code)
            if fs_storage:
                fs = fs_storage.fs
        return fs

    @api.model
    @tools.ormcache("model_name", "field_name")
    def get_storage_code_by_model_field(self, model_name, field_name=None):
        """Return the storage backend associated to the given model and field.

        :param model_name: the name of the model
        :param field_name (optionnal): the name of the field
        """
        if field_name and model_name:
            field = (
                self.env["ir.model.fields"]
                .sudo()
                .search(
                    [("model", "=", model_name), ("name", "=", field_name)], limit=1
                )
            )
            if field:
                storage = (
                    self.env["fs.storage"]
                    .sudo()
                    .search([])
                    .filtered_domain([("field_ids", "in", [field.id])])
                )
                if storage:
                    return storage.code
        if model_name:
            model = (
                self.env["ir.model"]
                .sudo()
                .search([("model", "=", model_name)], limit=1)
            )
            if model:
                storage = (
                    self.env["fs.storage"]
                    .sudo()
                    .search([])
                    .filtered_domain([("model_ids", "in", [model.id])])
                )
                if storage:
                    return storage.code
        return None

    @api.model
    def _get_fs_by_model_field(self, model_name, field_name=None):
        """Return the filesystem associated to the given model and field.

        :param model_name: the name of the model
        :param field_name (optionnal): the name of the field
        """
        code = self.get_storage_code_by_model_field(model_name, field_name)
        if not code:
            raise ValueError(
                f"No storage found for model {model_name} and field {field_name}"
            )
        return self.get_fs_by_code(code)

    def copy(self, default=None):
        default = default or {}
        if "code" not in default:
            default["code"] = f"{self.code}_copy"
        return super().copy(default)

    @api.model
    def _get_protocols(self) -> list[tuple[str, str]]:
        protocol = [("odoofs", "Odoo's FileSystem")]
        for p in fsspec.available_protocols():
            try:
                cls = fsspec.get_filesystem_class(p)
                protocol.append((p, f"{p} ({cls.__name__})"))
            except Exception as e:
                _logger.debug("Cannot load the protocol %s. Reason: %s", p, e)
        return protocol

    @api.constrains("options")
    def _check_options(self) -> None:
        for rec in self:
            try:
                json.loads(rec.options or "{}")
            except Exception as e:
                raise ValidationError(_("The options must be a valid JSON")) from e

    @api.depends("options")
    def _compute_json_options(self) -> None:
        for rec in self:
            rec.json_options = json.loads(rec.options or "{}")

    def _inverse_json_options(self) -> None:
        for rec in self:
            rec.options = json.dumps(rec.json_options)

    @api.depends("protocol")
    def _compute_protocol_descr(self) -> None:
        for rec in self:
            rec.protocol_descr = fsspec.get_filesystem_class(rec.protocol).__doc__
            rec.options_protocol = rec.protocol

    @api.model
    def _get_options_protocol(self) -> list[tuple[str, str]]:
        protocol = [("odoofs", "Odoo's Filesystem")]
        for p in fsspec.available_protocols():
            try:
                fsspec.get_filesystem_class(p)
                protocol.append((p, p))
            except Exception as e:
                _logger.debug("Cannot load the protocol %s. Reason: %s", p, e)
        return protocol

    @api.depends("options_protocol")
    def _compute_options_properties(self) -> None:
        for rec in self:
            cls = fsspec.get_filesystem_class(rec.options_protocol)
            signature = inspect.signature(cls.__init__)
            doc = inspect.getdoc(cls.__init__)
            rec.options_properties = f"__init__{signature}\n{doc}"

    @api.depends("model_xmlids")
    def _compute_model_ids(self):
        """
        Use the char field (containing all model xmlids) to fulfill the o2m field.
        """
        for rec in self:
            xmlids = (
                rec.model_xmlids.split(",") if isinstance(rec.model_xmlids, str) else []
            )
            model_ids = []
            for xmlid in xmlids:
                # Method returns False if no model is found for this xmlid
                model_id = self.env["ir.model.data"]._xmlid_to_res_id(xmlid)
                if model_id:
                    model_ids.append(model_id)
            rec.model_ids = [(6, 0, model_ids)]

    def _inverse_model_ids(self):
        """
        When the model_ids o2m field is updated, re-compute the char list
        of model XML ids.
        """
        for rec in self:
            xmlids = models.Model.get_external_id(rec.model_ids).values()
            rec.model_xmlids = ",".join(xmlids)

    @api.depends("field_xmlids")
    def _compute_field_ids(self):
        """
        Use the char field (containing all field xmlids) to fulfill the o2m field.
        """
        for rec in self:
            xmlids = (
                rec.field_xmlids.split(",") if isinstance(rec.field_xmlids, str) else []
            )
            field_ids = []
            for xmlid in xmlids:
                # Method returns False if no field is found for this xmlid
                field_id = self.env["ir.model.data"]._xmlid_to_res_id(xmlid)
                if field_id:
                    field_ids.append(field_id)
            rec.field_ids = [(6, 0, field_ids)]

    def _inverse_field_ids(self):
        """
        When the field_ids o2m field is updated, re-compute the char list
        of field XML ids.
        """
        for rec in self:
            xmlids = models.Model.get_external_id(rec.field_ids).values()
            rec.field_xmlids = ",".join(xmlids)

    def _get_marker_file_name(self):
        return f".odoo_fs_storage_{self.id}.marker"

    def _marker_file_check_connection(self, fs):
        marker_file_name = self._get_marker_file_name()
        try:
            fs.info(marker_file_name)
        except FileNotFoundError:
            fs.touch(marker_file_name)

    def _ls_check_connection(self, fs):
        # NOTE: run 'ls' on a non existing file to get better perf on FS
        # having a huge amount of files in root folder.
        # Getting a 'FileNotFoundError' means that the connection is working well.
        try:
            fs.ls(LS_NON_EXISTING_FILE, detail=False)
        # pylint: disable=except-pass
        except FileNotFoundError:
            pass

    def _check_connection(self, fs, check_connection_method):
        if check_connection_method == "marker_file":
            self._marker_file_check_connection(fs)
        elif check_connection_method == "ls":
            self._ls_check_connection(fs)
        return True

    @property
    def fs(self) -> fsspec.AbstractFileSystem:
        """Get the fsspec filesystem for this backend."""
        self.ensure_one()
        if not self.__fs:
            self.__fs = self.sudo()._get_filesystem()
        if not tools.config["test_enable"]:
            # Check whether we need to invalidate FS cache or not.
            # Use a marker file to limit the scope of the LS command for performance.
            try:
                self._check_connection(self.__fs, self.check_connection_method)
            except Exception as e:
                self.__fs.clear_instance_cache()
                self.__fs = None
                raise e
        return self.__fs

    def _get_filesystem_storage_path(self) -> str:
        """Get the path to the storage directory.

        This path is relative to the odoo filestore.and is used as root path
        when the protocol is filesystem.
        """
        self.ensure_one()
        path = os.path.join(self.env["ir.attachment"]._filestore(), "storage")
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    @property
    def _odoo_storage_path(self) -> str:
        """Get the path to the storage directory.

        This path is relative to the odoo filestore.and is used as root path
        when the protocol is filesystem.
        """
        if not self.__odoo_storage_path:
            self.__odoo_storage_path = self._get_filesystem_storage_path()
        return self.__odoo_storage_path

    def _recursive_add_odoo_storage_path(self, options: dict) -> dict:
        """Add the odoo storage path to the options.

        This is a recursive function that will add the odoo_storage_path
        option to the nested target_options if the target_protocol is
        odoofs
        """
        if "target_protocol" in options:
            target_options = options.get("target_options", {})
            if options["target_protocol"] == "odoofs":
                target_options["odoo_storage_path"] = self._odoo_storage_path
                options["target_options"] = target_options
            self._recursive_add_odoo_storage_path(target_options)
        return options

    def _eval_options_from_env(self, options):
        values = {}
        for key, value in options.items():
            if isinstance(value, dict):
                values[key] = self._eval_options_from_env(value)
            elif isinstance(value, str) and value.startswith("$"):
                env_variable_name = value[1:]
                env_variable_value = os.getenv(env_variable_name)
                if env_variable_value is not None:
                    values[key] = env_variable_value
                else:
                    values[key] = value
                    _logger.warning(
                        "Environment variable %s is not set for fs_storage %s.",
                        env_variable_name,
                        self.display_name,
                    )
            else:
                values[key] = value
        return values

    def _get_fs_options(self):
        options = self.json_options
        if not self.eval_options_from_env:
            return options
        return self._eval_options_from_env(self.json_options)

    def _get_filesystem(self) -> fsspec.AbstractFileSystem:
        """Get the fsspec filesystem for this backend.

        See https://filesystem-spec.readthedocs.io/en/latest/api.html
        #fsspec.spec.AbstractFileSystem

        :return: fsspec.AbstractFileSystem
        """
        self.ensure_one()
        options = self._get_fs_options()
        if self.protocol == "odoofs":
            options["odoo_storage_path"] = self._odoo_storage_path
        # Webdav protocol handler does need the auth to be a tuple not a list !
        if (
            self.protocol == "webdav"
            and "auth" in options
            and isinstance(options["auth"], list)
        ):
            options["auth"] = tuple(options["auth"])
        options = self._recursive_add_odoo_storage_path(options)
        fs = fsspec.filesystem(self.protocol, **options)
        directory_path = self.get_directory_path()
        if directory_path:
            fs = fsspec.filesystem("rooted_dir", path=directory_path, fs=fs)
        return fs

    # Deprecated methods used to ease the migration from the storage_backend addons
    # to the fs_storage addons. These methods will be removed in the future (Odoo 18)
    @deprecated("Please use _get_filesystem() instead and the fsspec API directly.")
    def add(self, relative_path, data, binary=True, **kwargs) -> None:
        if not binary:
            data = base64.b64decode(data)
        path = relative_path.split(self.fs.sep)[:-1]
        if not self.fs.exists(self.fs.sep.join(path)):
            self.fs.makedirs(self.fs.sep.join(path))
        with self.fs.open(relative_path, "wb", **kwargs) as f:
            f.write(data)

    @deprecated("Please use _get_filesystem() instead and the fsspec API directly.")
    def get(self, relative_path, binary=True, **kwargs) -> AnyStr:
        data = self.fs.read_bytes(relative_path, **kwargs)
        if not binary and data:
            data = base64.b64encode(data)
        return data

    @deprecated("Please use _get_filesystem() instead and the fsspec API directly.")
    def list_files(self, relative_path="", pattern=False) -> list[str]:
        relative_path = relative_path or self.fs.root_marker
        if not self.fs.exists(relative_path):
            return []
        if pattern:
            relative_path = self.fs.sep.join([relative_path, pattern])
            return self.fs.glob(relative_path)
        return self.fs.ls(relative_path, detail=False)

    @deprecated("Please use _get_filesystem() instead and the fsspec API directly.")
    def find_files(self, pattern, relative_path="", **kw) -> list[str]:
        """Find files matching given pattern.

        :param pattern: regex expression
        :param relative_path: optional relative path containing files
        :return: list of file paths as full paths from the root
        """
        result = []
        relative_path = relative_path or self.fs.root_marker
        if not self.fs.exists(relative_path):
            return []
        regex = re.compile(pattern)
        for file_path in self.fs.ls(relative_path, detail=False):
            # fs.ls returns a relative path
            if regex.match(os.path.basename(file_path)):
                result.append(file_path)
        return result

    @deprecated("Please use _get_filesystem() instead and the fsspec API directly.")
    def move_files(self, files, destination_path, **kw) -> None:
        """Move files to given destination.

        :param files: list of file paths to be moved
        :param destination_path: directory path where to move files
        :return: None
        """
        for file_path in files:
            self.fs.move(
                file_path,
                self.fs.sep.join([destination_path, os.path.basename(file_path)]),
                **kw,
            )

    @deprecated("Please use _get_filesystem() instead and the fsspec API directly.")
    def delete(self, relative_path) -> None:
        self.fs.rm_file(relative_path)

    def action_test_config(self):
        self.ensure_one()
        if self.check_connection_method:
            return self._test_config(self.check_connection_method)
        else:
            action = self.env["ir.actions.actions"]._for_xml_id(
                "fs_storage.act_open_fs_test_connection_view"
            )
            action["context"] = {"active_model": "fs.storage", "active_id": self.id}
            return action

    def _test_config(self, connection_method):
        try:
            self._check_connection(self.fs, connection_method)
            title = _("Connection Test Succeeded!")
            message = _("Everything seems properly set up!")
            msg_type = "success"
        except Exception as err:
            title = _("Connection Test Failed!")
            message = str(err)
            msg_type = "danger"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": msg_type,
                "sticky": False,
            },
        }

    def _get_root_filesystem(self, fs=None):
        if not fs:
            self.ensure_one()
            fs = self.fs
        while hasattr(fs, "fs"):
            fs = fs.fs
        return fs
