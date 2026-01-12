# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
# Copyright 2020 ACSONE SA/NV (<http://acsone.eu>)
# @author Simone Orsi <simahawk@gmail.com>

import os
import re

from odoo.addons.component.core import AbstractComponent


class BaseStorageAdapter(AbstractComponent):
    _name = "base.storage.adapter"
    _collection = "storage.backend"

    def _fullpath(self, relative_path):
        dp = self.collection.directory_path
        if not dp or relative_path.startswith(dp):
            return relative_path
        return os.path.join(dp, relative_path)

    def add(self, relative_path, data, **kwargs):
        raise NotImplementedError

    def get(self, relative_path, **kwargs):
        raise NotImplementedError

    def list(self, relative_path=""):
        raise NotImplementedError

    def find_files(self, pattern, relative_path="", **kwargs):
        """Find files matching given pattern.

        :param pattern: regex expression
        :param relative_path: optional relative path containing files
        :return: list of file paths as full paths from the root
        """
        regex = re.compile(pattern)
        filelist = self.list(relative_path)
        files_matching = [
            regex.match(file_).group() for file_ in filelist if regex.match(file_)
        ]
        filepaths = []
        if files_matching:
            filepaths = [
                os.path.join(self._fullpath(relative_path) or "", filename)
                for filename in files_matching
            ]
        return filepaths

    def move_files(self, files, destination_path, **kwargs):
        """Move files to given destination.

        :param files: list of file paths to be moved
        :param destination_path: directory path where to move files
        :return: None
        """
        raise NotImplementedError

    def delete(self, relative_path):
        raise NotImplementedError

    # You can define `validate_config` on your own adapter
    # to make validation button available on UI.
    # This method should simply pass smoothly when validation is ok,
    # otherwise it should raise an exception.
    # def validate_config(self):
    #    raise NotImplementedError
