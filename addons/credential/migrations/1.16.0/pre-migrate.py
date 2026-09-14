from odoo import SUPERUSER_ID, api


def _hand_consumer_rows_to_their_field_owner(cr):
    cr.execute(
        """
        WITH consumer_rows AS (
            SELECT data.id,
                   data.name,
                   coalesce(
                       substring(data.name FROM '^selection__(.+)__auth_type__'),
                       substring(data.name FROM '^model_inherit__(.+)__mixin_credential_auth$')
                   ) AS table_name
              FROM ir_model_data data
             WHERE data.module = 'credential'
               AND data.model IN ('ir.model.fields.selection', 'ir.model.inherit')
        ),
        owned AS (
            SELECT consumer_rows.id, consumer_rows.name, owner.module
              FROM consumer_rows
              JOIN ir_model_data owner
                ON owner.model = 'ir.model.fields'
               AND owner.name = 'field_' || consumer_rows.table_name || '__auth_type'
               AND owner.module <> 'credential'
             WHERE consumer_rows.table_name IS NOT NULL
        )
        DELETE FROM ir_model_data duplicate
         USING owned
         WHERE duplicate.module = owned.module AND duplicate.name = owned.name
        """
    )
    cr.execute(
        """
        UPDATE ir_model_data data
           SET module = owner.module
          FROM ir_model_data owner
         WHERE data.module = 'credential'
           AND data.model IN ('ir.model.fields.selection', 'ir.model.inherit')
           AND owner.model = 'ir.model.fields'
           AND owner.module <> 'credential'
           AND owner.name = 'field_' || coalesce(
                   substring(data.name FROM '^selection__(.+)__auth_type__'),
                   substring(data.name FROM '^model_inherit__(.+)__mixin_credential_auth$')
               ) || '__auth_type'
        """
    )


def _install_integration_where_a_module_needs_it(cr):
    cr.execute(
        """
        SELECT 1
          FROM ir_module_module_dependency dependency
          JOIN ir_module_module dependent
            ON dependent.id = dependency.module_id
           AND dependent.state IN ('installed', 'to upgrade')
         WHERE dependency.name = 'integration'
         LIMIT 1
        """
    )
    if not cr.fetchone():
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["ir.module.module"].search(
        [("name", "=", "integration"), ("state", "=", "uninstalled")]
    ).button_install()


def migrate(cr, version):
    if not version:
        return
    _hand_consumer_rows_to_their_field_owner(cr)
    _install_integration_where_a_module_needs_it(cr)
