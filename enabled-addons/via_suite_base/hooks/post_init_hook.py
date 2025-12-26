# -*- coding: utf-8 -*-
"""
Post Installation Hook
=======================

"""

import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def _install_languages(env):
    """
    Install ViaSuite supported languages.

    Installs the following languages:
    - pt_BR: Portuguese (Brazil)
    - es_PY: Spanish (Paraguay)
    - en_US: English (US) - already installed by default
    - ar_SA: Arabic (Saudi Arabia)
    - zh_CN: Chinese (Simplified)

    Args:
        env: Odoo environment
    """
    languages = [
        ('pt_BR', 'Portuguese (Brazil)'),
        ('es_PY', 'Spanish (Paraguay)'),
        ('ar_SA', 'Arabic (Saudi Arabia)'),
        ('zh_CN', 'Chinese (Simplified)'),
    ]

    for lang_code, lang_name in languages:
        try:
            # Check if language is already installed
            existing = env['res.lang'].search([('code', '=', lang_code)], limit=1)
            if existing:
                _logger.info(f"  - {lang_name} ({lang_code}): already installed")
                continue

            # Install language
            wizard = env['base.language.install'].create({
                'lang': lang_code,
                'overwrite': False,
            })
            wizard.lang_install()
            _logger.info(f"  - {lang_name} ({lang_code}): installed ✓")

        except Exception as e:
            _logger.warning(f"  - {lang_name} ({lang_code}): failed to install - {str(e)}")


def post_init_hook(env):
    """
    Post-installation hook for via_suite_base module.

    This function is called after the module is installed and performs
    all necessary initialization and customization tasks.

    Args:
        env: Odoo Environment
    """
    _logger.info("="*80)
    _logger.info("Starting ViaSuite Base post-installation...")
    _logger.info("="*80)

    # env is passed directly in Odoo 19+
    cr = env.cr

    try:
        # Step 1: Initialize Sentry error tracking
        # _logger.info("[1/7] Initializing Sentry error tracking...")
        # from odoo.addons.via_suite_base.hooks.sentry_init import initialize_sentry
        # sentry_ok = initialize_sentry()
        # if sentry_ok:
        #     _logger.info("✓ Sentry initialized successfully")
        # else:
        #     _logger.info("⊘ Sentry not configured (optional)")

        # Step 3: Install languages
        _logger.info("[3/8] Installing ViaSuite default languages...")
        _install_languages(env)
        _logger.info("✓ Languages installed (pt_BR, es_PY, en_US, ar_SA, zh_CN)")

        # Step 9: Configure mail server
        _logger.info("[8/9] Configuring mail server...")
        from odoo.addons.via_suite_base.hooks.mail_config import configure_mail_server
        mail_ok = configure_mail_server(env)
        if mail_ok:
            _logger.info("✓ Mail server configured from environment variables")
        else:
            _logger.warning("✗ Failed to configure mail server")

        # # Step 10: Configure OAuth
        # _logger.info("[10/10] Configuring OAuth...")
        # from odoo.addons.via_suite_base.hooks.oauth_config import configure_oauth
        # oauth_ok = configure_oauth(env)
        # if oauth_ok:
        #     _logger.info("✓ OAuth provider configured from environment variables")
        # else:
        #     _logger.warning("✗ Failed to configure OAuth provider")

        # Commit changes
        cr.commit()

        _logger.info("="*80)
        _logger.info("✓ ViaSuite Base installation complete!")
        _logger.info("="*80)

    except Exception as e:
        _logger.error("="*80)
        _logger.error("✗ Error during ViaSuite Base installation!")
        _logger.error(f"Error: {str(e)}")
        _logger.error("="*80)

        # # Try to capture error in Sentry if available
        # try:
        #     from odoo.addons.via_suite_base.hooks.sentry_init import SentryInitializer
        #     SentryInitializer.capture_exception(
        #         e,
        #         context={'phase': 'post_init_hook'}
        #     )
        # except Exception:
        #     pass

        raise