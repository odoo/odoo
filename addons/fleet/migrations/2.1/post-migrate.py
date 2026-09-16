from odoo.db.schema import column_exists


def migrate(cr, version):
    if not version:
        return
    _migrate_managers(cr)
    _drop_driver_subtype(cr)


def _migrate_managers(cr):
    # The fleet manager was a user column on the vehicle; every holder of an
    # asset is an assignment now, so the manager is one too.
    if not column_exists(cr, "resource_asset", "manager_id"):
        return
    cr.execute(
        """
        INSERT INTO resource_assignment
               (resource_id, assignee_id, role, date_start, active,
                create_uid, write_uid, create_date, write_date)
        SELECT asset.resource_id, holder.id, 'manager', now() AT TIME ZONE 'UTC', TRUE,
               1, 1, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC'
          FROM resource_asset asset
          JOIN res_users manager ON manager.id = asset.manager_id
          JOIN resource_resource holder
            ON holder.partner_id = manager.partner_id
           AND holder.resource_type = 'user'
           AND (holder.company_id = asset.company_id OR holder.company_id IS NULL)
         WHERE asset.manager_id IS NOT NULL
           AND NOT EXISTS (
               SELECT 1 FROM resource_assignment existing
                WHERE existing.resource_id = asset.resource_id
                  AND existing.role = 'manager'
                  AND existing.date_end IS NULL
           )
        """
    )
    cr.execute("ALTER TABLE resource_asset DROP COLUMN manager_id")


def _drop_driver_subtype(cr):
    cr.execute(
        """
        SELECT old.res_id, new.res_id
          FROM ir_model_data old, ir_model_data new
         WHERE old.module = 'fleet' AND old.name = 'mt_fleet_driver_updated'
           AND new.module = 'resource_asset'
           AND new.name = 'mt_asset_operator_updated'
        """
    )
    row = cr.fetchone()
    if not row:
        return
    old_id, new_id = row
    cr.execute(
        "UPDATE mail_message SET subtype_id = %s WHERE subtype_id = %s",
        [new_id, old_id],
    )
    cr.execute(
        "UPDATE mail_followers_mail_message_subtype_rel SET mail_message_subtype_id = %s "
        "WHERE mail_message_subtype_id = %s AND NOT EXISTS ("
        "    SELECT 1 FROM mail_followers_mail_message_subtype_rel other"
        "     WHERE other.mail_followers_id = mail_followers_mail_message_subtype_rel.mail_followers_id"
        "       AND other.mail_message_subtype_id = %s)",
        [new_id, old_id, new_id],
    )
    cr.execute(
        "DELETE FROM mail_followers_mail_message_subtype_rel WHERE mail_message_subtype_id = %s",
        [old_id],
    )
    cr.execute("DELETE FROM mail_message_subtype WHERE id = %s", [old_id])
    cr.execute(
        "DELETE FROM ir_model_data WHERE module = 'fleet' AND name = 'mt_fleet_driver_updated'"
    )
