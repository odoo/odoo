# Based on Florent Xicluna original code. Copyright Wingo SA
# Adapted by Nicolas Bessi. Copyright Camptocamp SA
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

import configparser
import logging
import os
from itertools import chain

from lxml import etree

from odoo import api, fields, models
from odoo.tools.config import config as system_base_config

from odoo.fields import Json

from .system_info import get_server_environment

_logger = logging.getLogger(__name__)

try:
    from odoo.addons import server_environment_files

    _dir = os.path.dirname(server_environment_files.__file__)
except ImportError:
    _logger.info(
        "not using server_environment_files for configuration, no directory found"
    )
    _dir = None

ENV_VAR_NAMES = ("SERVER_ENV_CONFIG", "SERVER_ENV_CONFIG_SECRET")

# Same dict as RawConfigParser._boolean_states
_boolean_states = {
    "1": True,
    "yes": True,
    "true": True,
    "on": True,
    "0": False,
    "no": False,
    "false": False,
    "off": False,
}


def _load_running_env():
    if not system_base_config.get("running_env"):
        env_running_env = os.environ.get("RUNNING_ENV", os.environ.get("ODOO_STAGE"))
        if env_running_env:
            system_base_config["running_env"] = env_running_env
        else:
            _logger.info(
                "`running_env` or `RUNNING_ENV`, `ODOO_STAGE` not found. "
                "Using default = `test`."
            )
            _logger.info(
                "We strongly recommend against using the rc file but instead use an "
                "explicit config file or env variable."
            )
            # safe default
            system_base_config["running_env"] = "test"


_load_running_env()


ck_path = None
if _dir:
    ck_path = os.path.join(_dir, system_base_config["running_env"])

    if not os.path.exists(ck_path):
        raise Exception(
            "Provided server environment does not exist, "
            f"please add a folder {ck_path}"
        )


def setboolean(obj, attr, _bool=None):
    """Replace the attribute with a boolean."""
    if _bool is None:
        _bool = dict(_boolean_states)
    res = _bool[getattr(obj, attr).lower()]
    setattr(obj, attr, res)
    return res


# Borrowed from MarkupSafe
def _escape(s):
    """Convert the characters &<>'" in string s to HTML-safe sequences."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace(">", "&gt;")
        .replace("<", "&lt;")
        .replace("'", "&#39;")
        .replace('"', "&#34;")
    )


def _listconf(env_path):
    """List configuration files in a folder."""
    files = [
        os.path.join(env_path, name)
        for name in sorted(os.listdir(env_path))
        if name.endswith(".conf")
    ]
    return files


def _load_config_from_server_env_files(config_p):
    default = os.path.join(_dir, "default")
    running_env = os.path.join(_dir, system_base_config["running_env"])
    if os.path.isdir(default):
        conf_files = _listconf(default) + _listconf(running_env)
    else:
        conf_files = _listconf(running_env)

    try:
        config_p.read(conf_files)
    except Exception as e:
        raise Exception(f'Cannot read config files "{conf_files}":  {e}') from e


def _load_config_from_rcfile(config_p):
    config_p.read(system_base_config.rcfile)
    config_p.remove_section("options")


def _load_config_from_env(config_p):
    for varname in ENV_VAR_NAMES:
        env_config = os.getenv(varname)
        if env_config:
            try:
                config_p.read_string(env_config)
            except configparser.Error as err:
                raise Exception(
                    f"{varname} content could not be parsed: {err}"
                ) from err


def _load_config():
    """Load the configuration and return a ConfigParser instance."""
    config_p = configparser.ConfigParser()
    # options are case-sensitive
    config_p.optionxform = str

    if _dir:
        _load_config_from_server_env_files(config_p)
    _load_config_from_rcfile(config_p)
    _load_config_from_env(config_p)
    return config_p


serv_config = _load_config()


class _Defaults(dict):
    __slots__ = ()

    def __setitem__(self, key, value):
        def func(*a):
            return str(value)

        return dict.__setitem__(self, key, func)


class ServerConfiguration(models.TransientModel):
    """Display server configuration."""

    _name = "server.config"
    _description = "Display server configuration"
    _conf_defaults = _Defaults()

    config = Json()

    @classmethod
    def _build_model(cls, pool, cr):
        """Add columns to model dynamically
        and init some properties

        """
        ModelClass = super()._build_model(pool, cr)
        ModelClass._add_columns()
        ModelClass._arch = None
        ModelClass._build_osv()
        return ModelClass

    @classmethod
    def _format_key(cls, section, key):
        return f"{section}_I_{key}"

    @property
    def show_passwords(self):
        return system_base_config["running_env"] in ("dev",)

    @classmethod
    def _format_key_display_name(cls, key_name):
        return key_name.replace("_I_", " | ")

    @classmethod
    def _add_columns(cls):
        """Add columns to model dynamically"""
        cols = chain(
            list(cls._get_base_cols().items()),
            list(cls._get_env_cols().items()),
            list(cls._get_system_cols().items()),
        )
        for col, value in cols:
            col_name = col.replace(".", "_")
            tmp_field = fields.Char(
                string=cls._format_key_display_name(col_name),
                sparse="config",
                readonly=True,
            )
            setattr(
                ServerConfiguration,
                col_name,
                tmp_field,
            )
            tmp_field.name = col_name
            ServerConfiguration._field_definitions.append(tmp_field)
            cls._conf_defaults[col_name] = value

    @classmethod
    def _get_base_cols(cls):
        """Compute base fields"""
        res = {}
        for col, item in list(system_base_config.options.items()):
            key = cls._format_key("odoo", col)
            res[key] = item
        return res

    @classmethod
    def _get_env_cols(cls, sections=None):
        """Compute base fields"""
        res = {}
        sections = sections if sections else serv_config.sections()
        for section in sections:
            for col, item in serv_config.items(section):
                key = cls._format_key(section, col)
                res[key] = item
        return res

    @classmethod
    def _get_system_cols(cls):
        """Compute system fields"""
        res = {}
        for col, item in get_server_environment():
            key = cls._format_key("system", col)
            res[key] = item
        return res

    @classmethod
    def _group(cls, items):
        """Return an XML chunk which represents a group of fields."""
        names = []

        for key in sorted(items):
            names.append(key.replace(".", "_"))
        return (
            '<group col="2" colspan="4">'
            + "".join(
                [f'<field name="{_escape(name)}" readonly="1"/>' for name in names]
            )
            + "</group>"
        )

    @classmethod
    def _build_osv(cls):
        """Build the view for the current configuration."""
        arch = '<form string="Configuration Form">' '<notebook colspan="4">'

        # Odoo server configuration
        rcfile = system_base_config.rcfile
        items = cls._get_base_cols()
        arch += '<page string="Odoo">'
        arch += f'<separator string="{_escape(rcfile)}" colspan="4"/>'
        arch += cls._group(items)
        arch += '<separator colspan="4"/></page>'

        arch += '<page string="Environment based configurations">'
        for section in sorted(serv_config.sections()):
            items = cls._get_env_cols(sections=[section])
            arch += f'<separator string="[{_escape(section)}]" colspan="4"/>'
            arch += cls._group(items)
        arch += '<separator colspan="4"/></page>'

        # System information
        arch += '<page string="System">'
        arch += '<separator string="Server Environment" colspan="4"/>'
        arch += cls._group(cls._get_system_cols())
        arch += '<separator colspan="4"/></page>'

        arch += "</notebook></form>"
        cls._arch = etree.fromstring(arch)

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        res = super().get_view(view_id, view_type, **options)
        View = self.env["ir.ui.view"].browse(view_id)
        if view_type == "form":
            arch, models = View.postprocess_and_fields(
                self._arch, model=self._name, **options
            )
            res["arch"] = arch
        return res

    @api.model
    def _is_secret(self, key):
        """
        This method is intended to be inherited to define which values
        should be kept secret.
        :return: True if information has to be protected, False otherwise
        """
        secret_keys = ["_pass", "passw", "key", "secret", "token"]
        return any(secret_key in key for secret_key in secret_keys)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if not self.env.user.has_group(
            "server_environment.has_server_configuration_access"
        ):
            return res
        for key in self._conf_defaults:
            if key not in fields_list:
                continue
            if not self.show_passwords and self._is_secret(key=key):
                res[key] = "**********"
            else:
                res[key] = self._conf_defaults[key]()
        return res
