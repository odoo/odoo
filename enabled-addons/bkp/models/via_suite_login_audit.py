# -*- coding: utf-8 -*-
"""
Login Audit Model
==================

Stores login and logout events for security auditing.
"""

from odoo import models, fields, api
from odoo.addons.via_suite_base.utils.logger import get_logger

logger = get_logger(__name__)


class ViaSuiteLoginAudit(models.Model):
    """
    Login/Logout Audit Log

    Records authentication events including:
    - Successful logins
    - Failed login attempts
    - Logouts
    - Session information
    """

    _name = 'via.suite.login.audit'
    _description = 'ViaSuite Login Audit Log'
    _order = 'create_date desc'
    _rec_name = 'user_id'

    # User information
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade',
        index=True,
        help='User who attempted login'
    )

    user_email = fields.Char(
        string='Email',
        related='user_id.email',
        store=True,
        help='Email of the user'
    )

    # Event details
    event_type = fields.Selection([
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('failed_login', 'Failed Login'),
    ], string='Event Type', required=True, index=True)

    login_method = fields.Selection([
        ('oauth', 'OAuth (Keycloak)'),
        ('password', 'Password'),
        ('token', 'API Token'),
    ], string='Login Method', help='Authentication method used')

    # Session information
    session_id = fields.Char(
        string='Session ID',
        help='Session identifier'
    )

    # Network information
    ip_address = fields.Char(
        string='IP Address',
        help='IP address of the client'
    )

    user_agent = fields.Text(
        string='User Agent',
        help='Browser/client user agent string'
    )

    # Tenant information
    tenant_name = fields.Char(
        string='Tenant',
        help='Database/tenant name',
        index=True
    )

    # Additional context
    error_message = fields.Text(
        string='Error Message',
        help='Error message for failed login attempts'
    )

    success = fields.Boolean(
        string='Success',
        default=True,
        help='Whether the login was successful'
    )

    # Timestamps
    create_date = fields.Datetime(
        string='Event Time',
        readonly=True,
        index=True
    )

    @api.model
    def log_login_event(self, user_id, event_type, login_method=None,
                        session_id=None, ip_address=None, user_agent=None,
                        success=True, error_message=None):
        """
        Log a login/logout event.

        Args:
            user_id (int): ID of the user
            event_type (str): Type of event ('login', 'logout', 'failed_login')
            login_method (str): Method used for login
            session_id (str): Session identifier
            ip_address (str): Client IP address
            user_agent (str): Browser user agent
            success (bool): Whether the event was successful
            error_message (str): Error message if failed

        Returns:
            via.suite.login.audit: Created audit record
        """
        try:
            values = {
                'user_id': user_id,
                'event_type': event_type,
                'login_method': login_method,
                'session_id': session_id,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'tenant_name': self.env.cr.dbname,
                'success': success,
                'error_message': error_message,
            }

            audit_record = self.create(values)

            # Also log to structured logger
            logger.info(
                f"audit_{event_type}",
                user_id=user_id,
                event_type=event_type,
                login_method=login_method,
                tenant=self.env.cr.dbname,
                ip_address=ip_address,
                success=success
            )

            return audit_record

        except Exception as e:
            # Don't fail the login/logout if audit logging fails
            logger.error(
                "audit_log_error",
                error=str(e),
                event_type=event_type,
                user_id=user_id
            )
            return False

    @api.model
    def get_user_login_history(self, user_id, limit=50):
        """
        Get login history for a specific user.

        Args:
            user_id (int): User ID
            limit (int): Maximum number of records to return

        Returns:
            recordset: Audit log records
        """
        return self.search([
            ('user_id', '=', user_id)
        ], limit=limit, order='create_date desc')

    @api.model
    def get_failed_login_attempts(self, hours=24, limit=100):
        """
        Get recent failed login attempts.

        Useful for security monitoring and alerting.

        Args:
            hours (int): Look back this many hours
            limit (int): Maximum number of records

        Returns:
            recordset: Failed login audit records
        """
        from datetime import datetime, timedelta

        cutoff_time = datetime.now() - timedelta(hours=hours)

        return self.search([
            ('event_type', '=', 'failed_login'),
            ('create_date', '>=', cutoff_time)
        ], limit=limit, order='create_date desc')