# -*- coding: utf-8 -*-
"""
OAuth Tenant Validation Tests
==============================

Tests for Keycloak OAuth tenant validation functionality.
"""

from odoo.tests import common
from odoo.exceptions import AccessDenied


class TestOAuthTenantValidation(common.TransactionCase):
    """
    Test cases for OAuth tenant validation.

    Tests the logic that validates whether a user has access to
    a specific tenant based on their Keycloak attributes.
    """

    def setUp(self):
        """
        Set up test environment.
        """
        super(TestOAuthTenantValidation, self).setUp()

        # Create test user
        self.test_user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test@example.com',
            'email': 'test@example.com',
        })

    def test_validate_tenant_no_restrictions(self):
        """
        Test tenant validation when user has no restrictions.

        Users without via_suite_tenants attribute should have
        access to all tenants.
        """
        result = self.env['res.users']._validate_tenant_access(
            'loja1',
            []
        )
        self.assertTrue(result, "User without restrictions should have access")

    def test_validate_tenant_wildcard_access(self):
        """
        Test tenant validation with wildcard access.

        Users with '*' in allowed_tenants should have access to all tenants.
        """
        result = self.env['res.users']._validate_tenant_access(
            'loja1',
            ['*']
        )
        self.assertTrue(result, "User with wildcard should have access to all tenants")

    def test_validate_tenant_specific_access(self):
        """
        Test tenant validation with specific tenant access.

        Users should only have access to tenants in their allowed list.
        """
        # User has access to loja1
        result = self.env['res.users']._validate_tenant_access(
            'loja1',
            ['loja1', 'loja2']
        )
        self.assertTrue(result, "User should have access to allowed tenant")

        # User does not have access to loja3
        result = self.env['res.users']._validate_tenant_access(
            'loja3',
            ['loja1', 'loja2']
        )
        self.assertFalse(result, "User should not have access to non-allowed tenant")

    def test_validate_tenant_single_tenant(self):
        """
        Test tenant validation with single tenant access.
        """
        result = self.env['res.users']._validate_tenant_access(
            'loja1',
            ['loja1']
        )
        self.assertTrue(result, "User should have access to their single tenant")

        result = self.env['res.users']._validate_tenant_access(
            'loja2',
            ['loja1']
        )
        self.assertFalse(result, "User should not have access to other tenant")

    def test_check_tenant_access_method(self):
        """
        Test the check_tenant_access method on res.users.
        """
        # Test with no restrictions
        self.test_user.via_suite_tenants = False
        result = self.test_user.check_tenant_access('loja1')
        self.assertTrue(result, "User without restrictions should have access")

        # Test with wildcard
        self.test_user.via_suite_tenants = '*'
        result = self.test_user.check_tenant_access('loja1')
        self.assertTrue(result, "User with wildcard should have access")

        # Test with specific tenant
        self.test_user.via_suite_tenants = 'loja1,loja2'
        result = self.test_user.check_tenant_access('loja1')
        self.assertTrue(result, "User should have access to allowed tenant")

        result = self.test_user.check_tenant_access('loja3')
        self.assertFalse(result, "User should not have access to non-allowed tenant")

    def test_tenant_string_parsing(self):
        """
        Test that tenant strings are correctly parsed.

        The via_suite_tenants field can be:
        - Empty/False: no restrictions
        - '*': wildcard access
        - 'tenant1,tenant2,tenant3': comma-separated list
        """
        # Test comma-separated parsing with spaces
        self.test_user.via_suite_tenants = 'loja1, loja2 ,loja3'
        result = self.test_user.check_tenant_access('loja2')
        self.assertTrue(result, "Should correctly parse tenants with spaces")

    def test_create_oauth_user(self):
        """
        Test OAuth user creation with tenant attributes.
        """
        oauth_user_info = {
            'email': 'newuser@example.com',
            'name': 'New User',
            'via_suite_tenants': 'loja1,loja2',
        }

        # Create user
        user = self.env['res.users'].create_oauth_user(
            oauth_user_info,
            provider_id=1  # Mock provider ID
        )

        self.assertEqual(user.login, 'newuser@example.com')
        self.assertEqual(user.via_suite_tenants, 'loja1,loja2')
        self.assertTrue(user.check_tenant_access('loja1'))
        self.assertFalse(user.check_tenant_access('loja3'))

    def test_oauth_user_already_exists(self):
        """
        Test that creating an existing OAuth user returns the existing user.
        """
        # Create user first time
        oauth_user_info = {
            'email': 'existing@example.com',
            'name': 'Existing User',
        }

        user1 = self.env['res.users'].create_oauth_user(
            oauth_user_info,
            provider_id=1
        )

        # Try to create again
        user2 = self.env['res.users'].create_oauth_user(
            oauth_user_info,
            provider_id=1
        )

        self.assertEqual(user1.id, user2.id, "Should return existing user")


class TestLoginAudit(common.TransactionCase):
    """
    Test cases for login audit logging.
    """

    def setUp(self):
        """
        Set up test environment.
        """
        super(TestLoginAudit, self).setUp()

        self.test_user = self.env['res.users'].create({
            'name': 'Audit Test User',
            'login': 'audittest@example.com',
            'email': 'audittest@example.com',
        })

    def test_log_login_event(self):
        """
        Test logging a login event.
        """
        audit_record = self.env['via.suite.login.audit'].log_login_event(
            user_id=self.test_user.id,
            event_type='login',
            login_method='oauth',
            ip_address='192.168.1.1',
            success=True
        )

        self.assertTrue(audit_record, "Should create audit record")
        self.assertEqual(audit_record.user_id.id, self.test_user.id)
        self.assertEqual(audit_record.event_type, 'login')
        self.assertEqual(audit_record.login_method, 'oauth')
        self.assertEqual(audit_record.ip_address, '192.168.1.1')
        self.assertTrue(audit_record.success)

    def test_log_logout_event(self):
        """
        Test logging a logout event.
        """
        audit_record = self.env['via.suite.login.audit'].log_login_event(
            user_id=self.test_user.id,
            event_type='logout',
            session_id='test-session-123',
            ip_address='192.168.1.1',
            success=True
        )

        self.assertEqual(audit_record.event_type, 'logout')
        self.assertEqual(audit_record.session_id, 'test-session-123')

    def test_log_failed_login(self):
        """
        Test logging a failed login attempt.
        """
        audit_record = self.env['via.suite.login.audit'].log_login_event(
            user_id=self.test_user.id,
            event_type='failed_login',
            login_method='password',
            ip_address='192.168.1.1',
            success=False,
            error_message='Invalid credentials'
        )

        self.assertEqual(audit_record.event_type, 'failed_login')
        self.assertFalse(audit_record.success)
        self.assertEqual(audit_record.error_message, 'Invalid credentials')

    def test_get_user_login_history(self):
        """
        Test retrieving user login history.
        """
        # Create multiple audit records
        for i in range(5):
            self.env['via.suite.login.audit'].log_login_event(
                user_id=self.test_user.id,
                event_type='login',
                ip_address=f'192.168.1.{i}',
                success=True
            )

        # Get history
        history = self.env['via.suite.login.audit'].get_user_login_history(
            self.test_user.id,
            limit=3
        )

        self.assertEqual(len(history), 3, "Should return limited number of records")
        self.assertEqual(history[0].user_id.id, self.test_user.id)

    def test_get_failed_login_attempts(self):
        """
        Test retrieving recent failed login attempts.
        """
        # Create failed login attempts
        for i in range(3):
            self.env['via.suite.login.audit'].log_login_event(
                user_id=self.test_user.id,
                event_type='failed_login',
                ip_address='192.168.1.1',
                success=False
            )

        # Get failed attempts
        failed_attempts = self.env['via.suite.login.audit'].get_failed_login_attempts(
            hours=24,
            limit=10
        )

        self.assertGreaterEqual(len(failed_attempts), 3, "Should return failed attempts")
        for attempt in failed_attempts:
            self.assertEqual(attempt.event_type, 'failed_login')
            self.assertFalse(attempt.success)