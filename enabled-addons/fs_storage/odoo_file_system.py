# Copyright 2023 ACSONE SA/NV (https://www.acsone.eu).
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).


from fsspec.registry import register_implementation

from .rooted_dir_file_system import RootedDirFileSystem


class OdooFileSystem(RootedDirFileSystem):
    """A directory-based filesystem for Odoo.

    This filesystem is mounted from a specific subdirectory of the Odoo
    filestore directory.

    It extends the RootedDirFileSystem to avoid going outside the
    specific subdirectory nor the Odoo filestore directory.

    Parameters:
        odoo_storage_path: The path of the subdirectory of the Odoo filestore
            directory to mount. This parameter is required and is always provided
            by the Odoo FS Storage even if it is explicitly defined in the
            storage options.
        fs: AbstractFileSystem
            An instantiated filesystem to wrap.
        target_protocol, target_options:
            if fs is none, construct it from these
    """

    def __init__(
        self,
        *,
        odoo_storage_path,
        fs=None,
        target_protocol=None,
        target_options=None,
        **storage_options,
    ):
        if not odoo_storage_path:
            raise ValueError("odoo_storage_path is required")
        super().__init__(
            path=odoo_storage_path,
            fs=fs,
            target_protocol=target_protocol,
            target_options=target_options,
            **storage_options,
        )


register_implementation("odoofs", OdooFileSystem)
