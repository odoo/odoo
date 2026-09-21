r"""End-migration: the Cloud Drive bucket is imported into Documents.

This runs at the ``end`` stage, not ``post``, for one reason: the import needs
``document.document`` in the registry, and ``cloud_storage_s3`` depends on
``cloud_storage`` and ``credential`` only, so it is always loaded well before
``document``. As a post-migration the guard below could never pass, and the
absorption silently did nothing on every database that ran 3.0.0.
``run_end_migrations()`` walks the whole graph once every module is loaded.

The import writes no bytes: each object becomes an ``ir.attachment`` of type
``cloud_storage`` carrying the object's URL, so a 37 GB bucket costs rows, not
filestore.

Reachability is a *warning*, never a raise. An end-migration that raises rolls
back an upgrade that has otherwise fully succeeded, which is a far worse outcome
than leaving the drive unimported for another day. The dead app menu is retired
either way, so a database that cannot import still stops offering users a tile
whose client action no longer exists.
"""

import logging

from odoo import SUPERUSER_ID, api

from odoo.addons.cloud_storage_s3.tools import drive_import, s3

_logger = logging.getLogger(__name__)

DRIVE_MODULE = "cloud_drive_s3"
DRIVE_PARAM_BUCKET = "cloud_drive_s3.bucket_name"
DRIVE_PARAM_REGION = "cloud_drive_s3.region"
DRIVE_GROUP_TO_DOCUMENTS = {
    "group_drive_read": "document.group_documents_user",
    "group_drive_admin": "document.group_documents_manager",
}


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    icp = env["ir.config_parameter"].sudo()
    bucket = icp.get_param(DRIVE_PARAM_BUCKET)
    region = icp.get_param(DRIVE_PARAM_REGION)
    if not (bucket and region and _table_exists(cr, "cloud_drive_access")):
        return
    if "document.document" not in env:
        _logger.error(
            "cloud_storage_s3: Documents is not installed, so the Cloud Drive "
            "bucket %s cannot be imported; install it and upgrade this module "
            "again",
            bucket,
        )
        return
    if _import_bucket(env, bucket, region):
        icp.search([("key", "in", [DRIVE_PARAM_BUCKET, DRIVE_PARAM_REGION])]).unlink()
    _retire_dead_app(env)


def _table_exists(cr, table):
    cr.execute("SELECT to_regclass(%s)", [table])
    return cr.fetchone()[0] is not None


def _import_bucket(env, bucket, region):
    """True when the bucket was imported; False when it must be retried."""
    try:
        client = s3.get_client(env)
        client.head_bucket(Bucket=bucket)
    except Exception as exc:
        _logger.error(
            "cloud_storage_s3: the Amazon S3 keys stored for Cloud Storage cannot "
            "reach the Cloud Drive bucket '%s' (%s). Grant that IAM user "
            "s3:ListBucket, s3:GetObject and s3:DeleteObject on it, then upgrade "
            "this module again. The same keys sign every download, so importing "
            "with the drive's own credential instead would leave every imported "
            "file unreadable.",
            bucket,
            exc,
        )
        return False

    env.cr.execute(
        "SELECT path, user_id, access_level FROM cloud_drive_access WHERE active"
    )
    grants = [
        {"path": path, "user_id": user_id, "access_level": level}
        for path, user_id, level in env.cr.fetchall()
    ]
    result = drive_import.import_bucket(
        env, client, bucket, region, root_name="Cloud", grants=grants
    )
    _logger.info(
        "cloud_storage_s3: Cloud Drive bucket %s imported into Documents: %s",
        bucket,
        result,
    )
    for grant in result["skipped_grants"]:
        _logger.warning("cloud_storage_s3: Cloud Drive grant not mapped: %s", grant)
    _move_drive_groups(env)
    return True


def _move_drive_groups(env):
    for drive_group, documents_group in DRIVE_GROUP_TO_DOCUMENTS.items():
        source = env.ref(f"{DRIVE_MODULE}.{drive_group}", raise_if_not_found=False)
        if not source:
            continue
        env.ref(documents_group).sudo().user_ids |= source.user_ids


def _retire_dead_app(env):
    """The module's code is gone, so every record it installed is debris.

    Uninstall its data the way a module uninstall does, not by a hand-picked
    list: picking menus and client actions left its window actions, views,
    groups, selections and constraint behind. A record something still needs
    (the drive credential's category is ON DELETE RESTRICT) is kept, xmlid
    and all, by the routine itself.
    """
    env["ir.model.data"].sudo()._uninstall_module_data([DRIVE_MODULE])
    env.cr.execute(
        "UPDATE ir_module_module SET state = 'uninstalled' "
        "WHERE name = %s AND state != 'uninstalled'",
        [DRIVE_MODULE],
    )
    if env.cr.rowcount:
        _logger.info("cloud_storage_s3: %s retired", DRIVE_MODULE)
