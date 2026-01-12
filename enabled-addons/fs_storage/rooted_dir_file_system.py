# Copyright 2023 ACSONE SA/NV (https://www.acsone.eu).
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import os

from fsspec.implementations.dirfs import DirFileSystem
from fsspec.implementations.local import make_path_posix
from fsspec.registry import register_implementation


class RootedDirFileSystem(DirFileSystem):
    """A directory-based filesystem that uses path as a root.

    The main purpose of this filesystem is to ensure that paths are always
    a sub path of the initial path. IOW, it is not possible to go outside
    the initial path. That's the only difference with the DirFileSystem provided
    by fsspec.

    This one should be provided by fsspec itself. We should propose a PR.
    """

    def _join(self, path):
        path = super()._join(path)
        # Ensure that the path is a subpath of the root path by resolving
        # any relative paths.
        # Since the path separator is not always the same on all systems,
        # we need to normalize the path separator.
        path_posix = os.path.normpath(make_path_posix(path))
        root_posix = os.path.normpath(make_path_posix(self.path))
        if not path_posix.startswith(root_posix):
            raise PermissionError(
                f"Path {path} is not a subpath of the root path {self.path}"
            )
        return path


register_implementation("rooted_dir", RootedDirFileSystem)
