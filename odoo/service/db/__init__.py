from odoo.db import SYSTEM_DBS

from ._checks import (
    DBNAME_MAX_LENGTH,
    DBNAME_PATTERN,
    check_db_management_enabled,
    check_db_name,
    check_super,
)
from .dump import BACKUP_FORMATS, dump_db, dump_db_manifest, exp_dump
from .lifecycle import (
    DatabaseExists,
    _create_empty_database,
    drop_database,
    duplicate_database,
    rename_database,
    exp_create_database,
    exp_drop,
    exp_duplicate_database,
    exp_rename,
    get_database_identifier,
)
from .listing import (
    check_db_exposed,
    exp_db_exist,
    exp_list,
    exp_list_countries,
    exp_list_lang,
    exp_server_version,
    invalidate_catalog_caches,
    list_db_incompatible,
    list_dbs,
    register_catalog_listener,
)
from .restore import exp_restore, restore_db
from .rpc import dispatch, exp_change_admin_password, exp_migrate_databases

__all__ = (
    "BACKUP_FORMATS",
    "DBNAME_MAX_LENGTH",
    "DBNAME_PATTERN",
    "SYSTEM_DBS",
    "DatabaseExists",
    "_create_empty_database",
    "check_db_exposed",
    "check_db_management_enabled",
    "check_db_name",
    "check_super",
    "dispatch",
    "drop_database",
    "dump_db",
    "dump_db_manifest",
    "duplicate_database",
    "exp_change_admin_password",
    "exp_create_database",
    "exp_db_exist",
    "exp_drop",
    "exp_dump",
    "exp_duplicate_database",
    "exp_list",
    "exp_list_countries",
    "exp_list_lang",
    "exp_migrate_databases",
    "exp_rename",
    "exp_restore",
    "exp_server_version",
    "get_database_identifier",
    "invalidate_catalog_caches",
    "list_db_incompatible",
    "list_dbs",
    "register_catalog_listener",
    "rename_database",
    "restore_db",
)
