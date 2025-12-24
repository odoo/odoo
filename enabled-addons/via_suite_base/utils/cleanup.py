# -*- coding: utf-8 -*-
"""
Cleanup Utilities for ViaSuite
================================

Provides automated cleanup functions for:
- Expired sessions
- Old audit logs
- Orphan attachments in S3

These functions are called by scheduled cron jobs.
"""

from datetime import datetime, timedelta
from odoo import api, SUPERUSER_ID
from odoo.addons.via_suite_base.utils.logger import get_logger

logger = get_logger(__name__)


class CleanupManager:
    """
    Manager for automated cleanup tasks.

    Handles cleanup of expired sessions, old logs, and orphan attachments.
    """

    @staticmethod
    def cleanup_expired_sessions(env, days=30):
        """
        Remove expired sessions older than specified days.

        Args:
            env: Odoo environment
            days (int): Number of days to keep sessions (default: 30)

        Returns:
            int: Number of sessions deleted
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            # Find expired sessions
            sessions = env['ir.sessions'].search([
                ('expiration_date', '<', cutoff_date)
            ])

            count = len(sessions)
            sessions.unlink()

            logger.info(
                "cleanup_sessions_success",
                deleted_count=count,
                cutoff_days=days
            )

            return count

        except Exception as e:
            logger.error(
                "cleanup_sessions_error",
                error=str(e),
                cutoff_days=days
            )
            raise

    @staticmethod
    def cleanup_old_audit_logs(env, days=90):
        """
        Remove audit logs older than specified days.

        Args:
            env: Odoo environment
            days (int): Number of days to keep logs (default: 90)

        Returns:
            int: Number of logs deleted
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            # Find old audit logs
            logs = env['via.suite.login.audit'].search([
                ('create_date', '<', cutoff_date)
            ])

            count = len(logs)
            logs.unlink()

            logger.info(
                "cleanup_audit_logs_success",
                deleted_count=count,
                cutoff_days=days
            )

            return count

        except Exception as e:
            logger.error(
                "cleanup_audit_logs_error",
                error=str(e),
                cutoff_days=days
            )
            raise

    @staticmethod
    def cleanup_orphan_attachments(env):
        """
        Identify and quarantine orphan attachments in S3.

        Orphan attachments are those that:
        - Reference deleted records
        - Have no valid res_model/res_id

        Instead of deleting, moves to a 'quarantine' folder in S3.

        Args:
            env: Odoo environment

        Returns:
            dict: Statistics about cleanup operation
        """
        try:
            # Find attachments with invalid references
            attachments = env['ir.attachment'].search([
                '|',
                ('res_model', '=', False),
                ('res_id', '=', False)
            ])

            orphaned = []
            for attachment in attachments:
                # Check if record exists
                if attachment.res_model and attachment.res_id:
                    try:
                        record = env[attachment.res_model].browse(attachment.res_id)
                        if not record.exists():
                            orphaned.append(attachment)
                    except Exception:
                        # Model doesn't exist or access error
                        orphaned.append(attachment)
                else:
                    orphaned.append(attachment)

            # Move to quarantine (add prefix to storage path)
            quarantined_count = 0
            for attachment in orphaned:
                try:
                    # Add quarantine prefix to file_name
                    if attachment.store_fname:
                        attachment.store_fname = f"quarantine/{attachment.store_fname}"
                        quarantined_count += 1
                except Exception as e:
                    logger.warning(
                        "quarantine_attachment_failed",
                        attachment_id=attachment.id,
                        error=str(e)
                    )

            logger.info(
                "cleanup_attachments_success",
                total_checked=len(attachments),
                orphaned_found=len(orphaned),
                quarantined=quarantined_count
            )

            return {
                'total_checked': len(attachments),
                'orphaned_found': len(orphaned),
                'quarantined': quarantined_count,
            }

        except Exception as e:
            logger.error(
                "cleanup_attachments_error",
                error=str(e)
            )
            raise


# Cron job wrapper functions
def cron_cleanup_expired_sessions(env):
    """
    Cron job wrapper for cleaning expired sessions.

    Called by ir.cron scheduled job.
    """
    CleanupManager.cleanup_expired_sessions(env, days=30)


def cron_cleanup_old_audit_logs(env):
    """
    Cron job wrapper for cleaning old audit logs.

    Called by ir.cron scheduled job.
    """
    CleanupManager.cleanup_old_audit_logs(env, days=90)


def cron_cleanup_orphan_attachments(env):
    """
    Cron job wrapper for cleaning orphan attachments.

    Called by ir.cron scheduled job.
    """
    CleanupManager.cleanup_orphan_attachments(env)