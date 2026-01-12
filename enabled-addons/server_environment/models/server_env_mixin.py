# Copyright 2018 Camptocamp (https://www.camptocamp.com).
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

import logging
from functools import partialmethod

from lxml import etree

from odoo import api, fields, models

from odoo.fields import Json

from ..server_env import serv_config

_logger = logging.getLogger(__name__)


class _partialmethod(partialmethod):
    """Custom implementation of partialmethod.

    ``odoo.fields.determine`` requires inverse methods to have ``__name__`` attribute.
    Unfortunately with ``partialmethod`` this attribute is not propagated
    even by using ``functools.update_wrapper``.

    Introduced by https://github.com/odoo/odoo/commit/36544651f2049bcf18777091dbf02c9631b33243
    """

    def __init__(self, func, *args, **keywords):
        self.__name__ = keywords.pop("__name__", None)
        super().__init__(func, *args, **keywords)

    def __get__(self, obj, cls=None):
        res = super().__get__(obj, cls=cls)
        if self.__name__ is not None:
            res.__name__ = self.__name__
        return res


class ServerEnvMixin(models.AbstractModel):
    """Mixin to add server environment in existing models

    Usage
    -----

    ::

        class StorageBackend(models.Model):
            _name = "storage.backend"
            _inherit = ["storage.backend", "server.env.mixin"]

            @property
            def _server_env_fields(self):
                return {"directory_path": {}}

    With the snippet above, the "storage.backend" model now uses a server
    environment configuration for the field ``directory_path``.

    Under the hood, this mixin automatically replaces the original field
    by an env-computed field that reads from the configuration files.

    By default, it looks for the configuration in a section named
    ``[model_name.Record Name]`` where ``model_name`` is the ``_name`` of the
    model with ``.`` replaced by ``_``. Then in a global section which is only
    the name of the model. They can be customized by overriding the method
    :meth:`~_server_env_section_name` and
    :meth:`~_server_env_global_section_name`.

    For each field transformed to an env-computed field, a companion field
    ``<field>_env_default`` is automatically created. When its value is set
    and the configuration files do not contain a key for that field, the
    env-computed field uses the default value stored in database. If there is a
    key for this field but it is empty, the env-computed field has an empty
    value.

    Env-computed fields are conditionally editable, based on the absence
    of their key in environment configuration files. When edited, their
    value is stored in the database.

    Integration with keychain
    -------------------------
    The keychain addon is used account information, encrypting the password
    with a key per environment.

    The default behavior of server_environment is to store the default fields
    in a serialized field, so the password would lend there unencrypted.

    You can benefit from keychain by using custom compute/inverse methods to
    get/set the password field:

    ::

        class StorageBackend(models.Model):
            _name = 'storage.backend'
            _inherit = ['keychain.backend', 'collection.base']

            @property
            def _server_env_fields(self):
                base_fields = super()._server_env_fields
                sftp_fields = {
                    "sftp_server": {},
                    "sftp_port": {},
                    "sftp_login": {},
                    "sftp_password": {
                        "no_default_field": True,
                        "compute_default": "_compute_password",
                        "inverse_default": "_inverse_password",
                    },
                }
                sftp_fields.update(base_fields)
                return sftp_fields

    * ``no_default_field`` means that no new (sparse) field need to be
      created, it already is provided by keychain
    * ``compute_default`` is the name of the compute method to get the default
      value when no key is set in the configuration files.
      ``_compute_password`` is implemented by ``keychain.backend``.
    * ``inverse_default`` is the name of the compute method to set the default
      value when it is editable. ``_inverse_password`` is implemented by
      ``keychain.backend``.

    """

    _name = "server.env.mixin"
    _description = "Mixin to add server environment in existing models"

    server_env_defaults = Json()

    _server_env_getter_mapping = {
        "integer": "getint",
        "float": "getfloat",
        "monetary": "getfloat",
        "boolean": "getboolean",
        "char": "get",
        "selection": "get",
        "text": "get",
    }

    @property
    def _server_env_fields(self):
        """Dict of fields to replace by fields computed from env

        To override in models. The dictionary is:
        {'name_of_the_field': options}

        Where ``options`` is a dictionary::

            options = {
                "getter": "getint",
                "no_default_field": True,
                "compute_default": "_compute_password",
                "inverse_default": "_inverse_password",
            }

        * ``getter``: The configparser getter can be one of: get, getboolean,
          getint, getfloat. The getter is automatically inferred from the
          type of the field, so it shouldn't generally be needed to set it.
        * ``no_default_field``: disable creation of a field for storing
          the default value, must be used with ``compute_default`` and
          ``inverse_default``
        * ``compute_default``: name of a compute method to get the default
          value when no key is present in configuration files
        * ``inverse_default``: name of an inverse method to set the default
          value when the value is editable

        Example::

            @property
            def _server_env_fields(self):
                base_fields = super()._server_env_fields
                sftp_fields = {
                    "sftp_server": {},
                    "sftp_port": {},
                    "sftp_login": {},
                    "sftp_password": {},
                }
                sftp_fields.update(base_fields)
                return sftp_fields
        """
        return {}

    @api.model
    def _server_env_global_section_name(self):
        """Name of the global section in the configuration files

        Can be customized in your model
        """
        return self._name.replace(".", "_")

    _server_env_section_name_field = "name"

    def _server_env_section_name(self):
        """Name of the section in the configuration files

        Can be customized in your model
        """
        self.ensure_one()
        val = self[self._server_env_section_name_field]
        if not val:
            # special case: we have onchanges relying on tech_name
            # and we are testing them using `tests.common.Form`.
            # when the for is initialized there's no value yet.
            return
        base = self._server_env_global_section_name()
        return ".".join((base, val))

    def _server_env_read_from_config(self, field_name, config_getter):
        self.ensure_one()
        global_section_name = self._server_env_global_section_name()
        section_name = self._server_env_section_name()
        try:
            # at this point we should have checked that we have a key with
            # _server_env_has_key_defined so we are sure that the value is
            # either in the global or the record config
            getter = getattr(serv_config, config_getter)
            if section_name in serv_config and field_name in serv_config[section_name]:
                value = getter(section_name, field_name)
            else:
                value = getter(global_section_name, field_name)
        except Exception as e:
            _logger.error(
                "Unable to read field %s in section %s: %s", field_name, section_name, e
            )
            return False
        return value

    def _server_env_has_key_defined(self, field_name):
        self.ensure_one()
        global_section_name = self._server_env_global_section_name()
        section_name = self._server_env_section_name()
        has_global_config = (
            global_section_name in serv_config
            and field_name in serv_config[global_section_name]
        )
        has_config = (
            section_name in serv_config and field_name in serv_config[section_name]
        )
        return has_global_config or has_config

    def _compute_server_env_from_config(self, field_name, options):
        getter_name = options.get("getter") if options else None
        if not getter_name:
            field_type = self._fields[field_name].type
            getter_name = self._server_env_getter_mapping.get(field_type)
        if not getter_name:
            # if you get this message and the field is working as expected,
            # you may want to add the type in _server_env_getter_mapping
            _logger.warning(
                "server.env.mixin is used on a field of type %s, "
                "which may not be supported properly"
            )
            getter_name = "get"
        value = self._server_env_read_from_config(field_name, getter_name)
        self[field_name] = value

    def _compute_server_env_from_default(self, field_name, options):
        if options and options.get("compute_default"):
            getattr(self, options["compute_default"])()
        else:
            default_field = self._server_env_default_fieldname(field_name)
            if default_field:
                self[field_name] = self[default_field]
            else:
                self[field_name] = False

    def _compute_server_env(self):
        """Read values from environment configuration files

        If an env-computed field has no key in configuration files,
        read from the ``<field>_env_default`` field from database.
        """
        for record in self:
            for field_name, options in self._server_env_fields.items():
                if record._server_env_has_key_defined(field_name):
                    record._compute_server_env_from_config(field_name, options)

                else:
                    record._compute_server_env_from_default(field_name, options)

    def _inverse_server_env(self, field_name):
        options = self._server_env_fields[field_name]
        default_field = self._server_env_default_fieldname(field_name)
        is_editable_field = self._server_env_is_editable_fieldname(field_name)

        for record in self:
            # when we write in an env-computed field, if it is editable
            # we update the default value in database

            if record[is_editable_field]:
                if options and options.get("inverse_default"):
                    getattr(record, options["inverse_default"])()
                elif default_field:
                    record[default_field] = record[field_name]

    def _compute_server_env_is_editable(self):
        """Compute <field>_is_editable values

        We can edit an env-computed filed only if there is no key
        in any environment configuration file. If there is an empty
        key, it's an empty value so we can't edit the env-computed field.
        """
        # we can't group it with _compute_server_env otherwise when called
        # in ``_inverse_server_env`` it would reset the value of the field
        for record in self:
            for field_name in self._server_env_fields:
                is_editable_field = self._server_env_is_editable_fieldname(field_name)
                is_editable = not record._server_env_has_key_defined(field_name)
                record[is_editable_field] = is_editable

    def _server_env_view_set_readonly(self, view_arch):
        field_xpath = './/field[@name="%s"]'
        for field in self._server_env_fields:
            is_editable_field = self._server_env_is_editable_fieldname(field)
            for elem in view_arch.findall(field_xpath % field):
                # set env-computed fields to readonly if the configuration
                # files have a key set for this field
                elem.set("readonly", "not is_editable_field")
            if not view_arch.findall(field_xpath % is_editable_field):
                # add the _is_editable fields in the view for the 'attrs'
                # domain
                view_arch.append(
                    etree.Element("field", name=is_editable_field, invisible="1")
                )
        return view_arch

    def _fields_view_get(
        self, view_id=None, view_type="form", toolbar=False, submenu=False
    ):
        view_data = super()._fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
        )
        view_arch = etree.fromstring(view_data["arch"].encode("utf-8"))
        view_arch = self._server_env_view_set_readonly(view_arch)
        view_data["arch"] = etree.tostring(view_arch, encoding="unicode")
        return view_data

    def _server_env_default_fieldname(self, base_field_name):
        """Return the name of the field with default value"""
        options = self._server_env_fields[base_field_name]
        if options and options.get("no_default_field"):
            return ""
        return f"x_{base_field_name}_env_default"

    def _server_env_is_editable_fieldname(self, base_field_name):
        """Return the name of the field for "is editable"

        This is the field used to tell if the env-computed field can
        be edited.
        """
        return f"x_{base_field_name}_env_is_editable"

    def _server_env_transform_field_to_read_from_env(self, field):
        """Transform the original field in a computed field"""
        field.compute = "_compute_server_env"

        inverse_method_name = f"_inverse_server_env_{field.name}"
        inverse_method = _partialmethod(
            type(self)._inverse_server_env, field.name, __name__=inverse_method_name
        )
        setattr(type(self), inverse_method_name, inverse_method)
        field.inverse = inverse_method_name
        field.store = False
        field.required = False
        field.copy = False
        field.sparse = None
        field.prefetch = False

    def _server_env_add_is_editable_field(self, base_field):
        """Add a field indicating if we can edit the env-computed fields

        It is used in the inverse function of the env-computed field
        and in the views to add 'readonly' on the fields.
        """
        fieldname = self._server_env_is_editable_fieldname(base_field.name)
        # if the field is inherited, it's a related to its delegated model
        # (inherits), we want to override it with a new one
        if fieldname not in self._fields or self._fields[fieldname].inherited:
            field = fields.Boolean(
                compute="_compute_server_env_is_editable",
                automatic=True,
                # this is required to be able to edit fields
                # on new records
                default=True,
            )
            self._add_field(fieldname, field)

    def _server_env_add_default_field(self, base_field):
        """Add a field storing the default value

        The default value is used when there is no key for an env-computed
        field in the configuration files.

        The field is a sparse field stored in the serialized (json) field
        ``server_env_defaults``.
        """
        fieldname = self._server_env_default_fieldname(base_field.name)
        if not fieldname:
            return
        # if the field is inherited, it's a related to its delegated model
        # (inherits), we want to override it with a new one
        if fieldname not in self._fields or self._fields[fieldname].inherited:
            base_field_cls = base_field.__class__
            field_args = base_field.args.copy() if base_field.args else {}
            field_args.pop("_sequence", None)
            fieldlabel = "{} {}".format(base_field.string or "", "Env Default")
            field_args.update(
                {
                    "sparse": "server_env_defaults",
                    "automatic": True,
                    "string": fieldlabel,
                    "default": base_field.default,
                }
            )

            if hasattr(base_field, "selection"):
                field_args["selection"] = base_field.selection
            field = base_field_cls(**field_args)
            self._add_field(fieldname, field)

    @api.model
    def _setup_base(self):
        super()._setup_base()
        for fieldname in self._server_env_fields:
            field = self._fields[fieldname]
            self._server_env_add_default_field(field)
            self._server_env_transform_field_to_read_from_env(field)
            self._server_env_add_is_editable_field(field)
        return
