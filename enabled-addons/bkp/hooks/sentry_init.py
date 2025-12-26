# -*- coding: utf-8 -*-
"""
Sentry Initialization
=====================

Initializes Sentry error tracking for ViaSuite.

Configuration via environment variables:
- VIA_SUITE_SENTRY_DSN: Sentry DSN URL
- VIA_SUITE_SENTRY_ENVIRONMENT: Environment name (production, staging, dev)
- VIA_SUITE_SENTRY_TRACES_SAMPLE_RATE: Sample rate for performance tracing
"""

import os
import logging

_logger = logging.getLogger(__name__)


class SentryInitializer:
    """
    Initializes and configures Sentry for ViaSuite.
    """

    _initialized = False

    @classmethod
    def initialize(cls):
        """
        Initialize Sentry if DSN is configured.

        Returns:
            bool: True if Sentry was initialized, False otherwise
        """
        if cls._initialized:
            return True

        try:
            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingIntegration

            # Get configuration from environment
            dsn = os.getenv('VIA_SUITE_SENTRY_DSN')
            environment = os.getenv('VIA_SUITE_SENTRY_ENVIRONMENT', 'production')
            traces_sample_rate = float(os.getenv('VIA_SUITE_SENTRY_TRACES_SAMPLE_RATE', '0.1'))

            if not dsn:
                _logger.info("Sentry DSN not configured - skipping Sentry initialization")
                return False

            # Configure logging integration
            sentry_logging = LoggingIntegration(
                level=logging.INFO,        # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors as events
            )

            # Initialize Sentry
            sentry_sdk.init(
                dsn=dsn,
                environment=environment,
                traces_sample_rate=traces_sample_rate,
                integrations=[sentry_logging],

                # Set release version
                release=f"viasuite@19.0.1.0.0",

                # Send default PII (user info, IP addresses)
                send_default_pii=True,

                # Before send callback to add custom context
                before_send=cls._before_send_callback,
            )

            cls._initialized = True

            _logger.info(
                "Sentry initialized successfully",
                extra={
                    'environment': environment,
                    'traces_sample_rate': traces_sample_rate
                }
            )

            return True

        except ImportError:
            _logger.warning("sentry_sdk not installed - skipping Sentry initialization")
            return False
        except Exception as e:
            _logger.error(f"Failed to initialize Sentry: {str(e)}")
            return False

    @staticmethod
    def _before_send_callback(event, hint):
        """
        Callback to modify events before sending to Sentry.

        Adds custom context like tenant information.

        Args:
            event (dict): Sentry event
            hint (dict): Additional information

        Returns:
            dict: Modified event (or None to drop the event)
        """
        try:
            # Add custom tags
            if 'tags' not in event:
                event['tags'] = {}

            event['tags']['product'] = 'viasuite'

            # Try to add tenant information from thread local storage
            # (This would require additional implementation in request handling)

        except Exception as e:
            _logger.warning(f"Error in Sentry before_send callback: {str(e)}")

        return event

    @classmethod
    def capture_exception(cls, exception, **context):
        """
        Manually capture an exception to Sentry.

        Args:
            exception (Exception): Exception to capture
            **context: Additional context to include
        """
        if not cls._initialized:
            return

        try:
            import sentry_sdk

            with sentry_sdk.push_scope() as scope:
                # Add custom context
                for key, value in context.items():
                    scope.set_extra(key, value)

                sentry_sdk.capture_exception(exception)

        except Exception as e:
            _logger.error(f"Failed to capture exception in Sentry: {str(e)}")

    @classmethod
    def capture_message(cls, message, level='info', **context):
        """
        Manually capture a message to Sentry.

        Args:
            message (str): Message to capture
            level (str): Severity level (info, warning, error, fatal)
            **context: Additional context to include
        """
        if not cls._initialized:
            return

        try:
            import sentry_sdk

            with sentry_sdk.push_scope() as scope:
                # Add custom context
                for key, value in context.items():
                    scope.set_extra(key, value)

                sentry_sdk.capture_message(message, level=level)

        except Exception as e:
            _logger.error(f"Failed to capture message in Sentry: {str(e)}")


def initialize_sentry():
    """
    Convenience function to initialize Sentry.

    Returns:
        bool: True if initialized successfully
    """
    return SentryInitializer.initialize()