from odoo.db.schema import column_exists

# `res.users.apikeys` is `_auto = False`: its table is the model's own DDL,
# so the column it grew is added here, and the free string every key carried
# becomes a row of the scope model the ORM has just created.


def migrate(cr, version):
    if not version or not column_exists(cr, "res_users_apikeys", "scope"):
        return
    cr.execute(
        """
        INSERT INTO res_users_apikeys_scope (name, key, active, max_depth,
                                             budget_window_seconds, create_date, write_date)
        SELECT DISTINCT k.scope, k.scope, TRUE, 8, 60,
               now() at time zone 'UTC', now() at time zone 'UTC'
          FROM res_users_apikeys k
         WHERE k.scope IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM res_users_apikeys_scope s WHERE s.key = k.scope)
        """
    )
    if not column_exists(cr, "res_users_apikeys", "scope_id"):
        cr.execute(
            "ALTER TABLE res_users_apikeys ADD COLUMN scope_id integer "
            "REFERENCES res_users_apikeys_scope(id) ON DELETE CASCADE"
        )
    cr.execute(
        """
        UPDATE res_users_apikeys k
           SET scope_id = s.id
          FROM res_users_apikeys_scope s
         WHERE s.key = k.scope AND k.scope_id IS NULL
        """
    )
    cr.execute("ALTER TABLE res_users_apikeys DROP COLUMN scope")
