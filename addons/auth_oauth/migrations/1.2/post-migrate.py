def migrate(cr, version):
    cr.execute("ALTER TABLE res_users DROP COLUMN IF EXISTS oauth_access_token")
