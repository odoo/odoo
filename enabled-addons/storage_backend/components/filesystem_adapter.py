# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging
import os
import shutil

from odoo.exceptions import AccessError

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


def is_safe_path(basedir, path):
    return os.path.realpath(path).startswith(basedir)


class FileSystemStorageBackend(Component):
    _name = "filesystem.adapter"
    _inherit = "base.storage.adapter"
    _usage = "filesystem"

    def _basedir(self):
        return os.path.join(self.env["ir.attachment"]._filestore(), "storage")

    def _fullpath(self, relative_path):
        """This will build the full path for the file, we force to
        store the data inside the filestore in the directory 'storage".
        Becarefull if you implement your own custom path, end user
        should never be able to write or read unwanted filesystem file"""
        full_path = super()._fullpath(relative_path)
        base_dir = self._basedir()
        full_path = os.path.join(base_dir, full_path)
        if not is_safe_path(base_dir, full_path):
            raise AccessError(self.env._("Access to %s is forbidden") % full_path)
        return full_path

    def add(self, relative_path, data, **kwargs):
        full_path = self._fullpath(relative_path)
        dirname = os.path.dirname(full_path)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        with open(full_path, "wb") as my_file:
            my_file.write(data)

    def get(self, relative_path, **kwargs):
        full_path = self._fullpath(relative_path)
        with open(full_path, "rb") as my_file:
            data = my_file.read()
        return data

    def list(self, relative_path=""):
        full_path = self._fullpath(relative_path)
        if os.path.isdir(full_path):
            return os.listdir(full_path)
        return []

    def delete(self, relative_path):
        full_path = self._fullpath(relative_path)
        try:
            os.remove(full_path)
        except FileNotFoundError:
            _logger.warning("File not found in %s", full_path)

    def move_files(self, files, destination_path):
        result = []
        for file_path in files:
            if not os.path.exists(destination_path):
                os.makedirs(destination_path)
            filename = os.path.basename(file_path)
            destination_file = os.path.join(destination_path, filename)
            result.append(shutil.move(file_path, destination_file))
        return result
