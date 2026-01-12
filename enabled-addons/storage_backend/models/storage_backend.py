# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# Copyright 2019 Camptocamp SA (http://www.camptocamp.com).
# @author Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import fnmatch
import functools
import inspect
import logging
import warnings

from odoo import fields, models

_logger = logging.getLogger(__name__)


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


class StorageBackend(models.Model):
    _name = "storage.backend"
    _inherit = ["collection.base", "server.env.mixin"]
    _backend_name = "storage_backend"
    _description = "Storage Backend"

    name = fields.Char(required=True)
    backend_type = fields.Selection(
        selection=[("filesystem", "Filesystem")], required=True, default="filesystem"
    )
    directory_path = fields.Char(
        help="Relative path to the directory to store the file"
    )
    has_validation = fields.Boolean(compute="_compute_has_validation")

    def _compute_has_validation(self):
        for rec in self:
            if not rec.backend_type:
                # with server_env
                # this code can be triggered
                # before a backend_type has been set
                # get_adapter() can't work without backend_type
                rec.has_validation = False
                continue
            adapter = rec._get_adapter()
            rec.has_validation = hasattr(adapter, "validate_config")

    @property
    def _server_env_fields(self):
        return {"backend_type": {}, "directory_path": {}}

    def add(self, relative_path, data, binary=True, **kwargs):
        if not binary:
            data = base64.b64decode(data)
        return self._forward("add", relative_path, data, **kwargs)

    def get(self, relative_path, binary=True, **kwargs):
        data = self._forward("get", relative_path, **kwargs)
        if not binary and data:
            data = base64.b64encode(data)
        return data

    def list_files(self, relative_path="", pattern=False):
        names = self._forward("list", relative_path)
        if pattern:
            names = fnmatch.filter(names, pattern)
        return names

    def find_files(self, pattern, relative_path="", **kw):
        return self._forward("find_files", pattern, relative_path=relative_path)

    def move_files(self, files, destination_path, **kw):
        return self._forward("move_files", files, destination_path, **kw)

    def delete(self, relative_path):
        return self._forward("delete", relative_path)

    def _forward(self, method, *args, **kwargs):
        _logger.debug(
            "Backend Storage ID: %s type %s: %s file %s %s",
            self.backend_type,
            self.id,
            method,
            args,
            kwargs,
        )
        self.ensure_one()
        adapter = self._get_adapter()
        return getattr(adapter, method)(*args, **kwargs)

    def _get_adapter(self):
        with self.work_on(self._name) as work:
            return work.component(usage=self.backend_type)

    def action_test_config(self):
        if not self.has_validation:
            raise AttributeError("Validation not supported!")
        adapter = self._get_adapter()
        try:
            adapter.validate_config()
            title = self.env._("Connection Test Succeeded!")
            message = self.env._("Everything seems properly set up!")
            msg_type = "success"
        except Exception as err:
            title = self.env._("Connection Test Failed!")
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
