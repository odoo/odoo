# -*- coding: utf-8 -*-
"""
ViaSuite Custom Exceptions
===========================

Custom exception classes for better error handling and UX.
"""

from odoo.exceptions import AccessDenied


class ViaSuiteAuthError(AccessDenied):
    """Base exception for ViaSuite authentication errors."""
    
    def __init__(self, error_code, message="Authentication failed"):
        self.error_code = error_code
        super().__init__(message)


class TenantMismatchError(ViaSuiteAuthError):
    """Raised when user belongs to different tenant."""
    
    def __init__(self, user_tenant, current_db):
        self.user_tenant = user_tenant
        self.current_db = current_db
        super().__init__(
            'tenant_mismatch',
            f"Tenant mismatch: user belongs to '{user_tenant}' but trying to access '{current_db}'"
        )


class UserNotFoundError(ViaSuiteAuthError):
    """Raised when user doesn't exist in the system."""
    
    def __init__(self, email):
        self.email = email
        super().__init__(
            'user_not_found',
            f"User '{email}' not found in the system"
        )


class AccountDisabledError(ViaSuiteAuthError):
    """Raised when user account is disabled."""
    
    def __init__(self, email):
        self.email = email
        super().__init__(
            'account_disabled',
            f"Account '{email}' is disabled"
        )

class TenantInactiveError(ViaSuiteAuthError):
    """Raised when the tenant account is inactive."""
    
    def __init__(self, tenant_code):
        self.tenant_code = tenant_code
        super().__init__(
            'tenant_inactive',
            f"Tenant environment '{tenant_code}' is currently inactive"
        )
