# -*- coding: utf-8 -*-
"""
Logger Configuration
====================

Configures structured logging for ViaSuite.

Configuration via environment variables:
- VIA_SUITE_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
"""

import os
import logging
from odoo.addons.via_suite_base.utils.logger import ViaSuiteLogger

_logger = logging.getLogger(__name__)


class LoggerConfigurator:
    """
    Configures structured logging for ViaSuite.
    """

    _configured = False

    @classmethod
    def configure(cls):
        """
        Configure structured logging.

        Returns:
            bool: True if configured successfully
        """
        if cls._configured:
            return True

        try:
            # Get log level from environment
            log_level = os.getenv('VIA_SUITE_LOG_LEVEL', 'INFO').upper()

            # Validate log level
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if log_level not in valid_levels:
                _logger.warning(
                    f"Invalid log level '{log_level}', using INFO",
                    extra={'valid_levels': valid_levels}
                )
                log_level = 'INFO'

            # Configure ViaSuite logger
            ViaSuiteLogger.configure(log_level=log_level)

            cls._configured = True

            _logger.info(
                "Structured logging configured",
                extra={'log_level': log_level}
            )

            # Log a test message
            from odoo.addons.via_suite_base.utils.logger import get_logger
            test_logger = get_logger('via_suite_base.init')
            test_logger.info(
                "viasuite_logging_initialized",
                log_level=log_level,
                product='ViaSuite',
                version='19.0.1.0.0'
            )

            return True

        except Exception as e:
            _logger.error(f"Failed to configure structured logging: {str(e)}")
            return False


def configure_logging():
    """
    Convenience function to configure logging.

    Returns:
        bool: True if configured successfully
    """
    return LoggerConfigurator.configure()