from odoo.service import security

def allow_postgres_user(*args, **kwargs):
    return True

# Monkey patch the security check
security.check_postgres_user = allow_postgres_user
