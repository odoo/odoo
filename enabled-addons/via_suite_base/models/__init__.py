# -*- coding: utf-8 -*-
"""
ViaSuite Base Models
====================

Model customizations for ViaSuite:
- res_users: Session timeout, OAuth validation, login audit
- res_company: Default branding and settings
- auth_oauth: Keycloak tenant validation
- via_suite_login_audit: Login/logout audit logging
"""

from . import res_users
from . import res_company
from . import auth_oauth
from . import via_suite_login_audit