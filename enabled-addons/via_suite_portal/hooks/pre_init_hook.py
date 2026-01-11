# -*- coding: utf-8 -*-
import os
from odoo import api, SUPERUSER_ID
from odoo.exceptions import UserError

def pre_init_hook(env):
    """
    Validation hook to ensure via_suite_portal is only installed 
    on the authorized management database.
    """
    # Allow customization via environment variable, but default to your management DB
    allowed_db = os.getenv('VIA_SUITE_MANAGEMENT_DB', 'via-suite-viafronteira')
    current_db = env.cr.dbname

    if current_db != allowed_db:
        raise UserError(
            "Security Violation: The module 'via_suite_portal' is reserved for "
            f"the management database ('{allowed_db}').\n\n"
            f"Current database: '{current_db}'\n"
            "Installation aborted to prevent accidental deployment on a tenant environment."
        )
