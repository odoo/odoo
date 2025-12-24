# -*- coding: utf-8 -*-
"""
Post Installation Hook
=======================

Main orchestrator for ViaSuite Base module initialization.

This hook is called after the module is installed and coordinates:
1. Sentry initialization
2. Structured logging configuration
3. Language installation (pt_BR, es_PY, ar_SA, zh_CN)
4. Branding customizations
5. Theme injection
6. Logo updates
7. Email template customization
8. Company defaults
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


def post_init_hook(cr, registry):
    """
    Post-installation hook for via_suite_base module.

    This function is called after the module is installed and performs
    all necessary initialization and customization tasks.

    Args:
        cr: Database cursor
        registry: Odoo registry
    """
    _logger.info("="*80)
    _logger.info("Starting ViaSuite Base post-installation...")
    _logger.info("="*80)

    env = api.Environment(cr, SUPERUSER_ID, {})

    try:
        # Step 1: Initialize Sentry error tracking
        _logger.info("[1/7] Initializing Sentry error tracking...")
        from odoo.addons.via_suite_base.hooks.sentry_init import initialize_sentry
        sentry_ok = initialize_sentry()
        if sentry_ok:
            _logger.info("✓ Sentry initialized successfully")
        else:
            _logger.info("⊘ Sentry not configured (optional)")

        # Step 2: Configure structured logging
        _logger.info("[2/8] Configuring structured logging...")
        from odoo.addons.via_suite_base.hooks.logger_config import configure_logging
        logging_ok = configure_logging()
        if logging_ok:
            _logger.info("✓ Structured logging configured")
        else:
            _logger.warning("✗ Failed to configure structured logging")

        # Step 3: Install languages
        _logger.info("[3/8] Installing ViaSuite languages...")
        _install_languages(env)
        _logger.info("✓ Languages installed (pt_BR, es_PY, en_US, ar_SA, zh_CN)")

        # Step 4: Apply branding replacements
        _logger.info("[4/8] Applying ViaSuite branding replacements...")
        from odoo.addons.via_suite_base.hooks.branding.branding_replacer import apply_branding_replacements
        stats = apply_branding_replacements(env)
        _logger.info(
            f"✓ Branding applied: {stats['views']} views, "
            f"{stats['menus']} menus, {stats['translations']} translations"
        )

        # Step 5: Inject theme variables
        _logger.info("[5/8] Injecting ViaSuite theme colors...")
        from odoo.addons.via_suite_base.hooks.branding.theme_injector import inject_theme_variables
        inject_theme_variables(env)
        _logger.info("✓ Theme colors injected (Orange: #FF730E, Navy: #002147)")

        # Step 6: Update logos
        _logger.info("[6/8] Updating system logos...")
        from odoo.addons.via_suite_base.hooks.branding.logo_updater import update_logos
        update_logos(env)
        _logger.info("✓ Logos updated")

        # Step 7: Customize email templates
        _logger.info("[7/8] Customizing email templates...")
        from odoo.addons.via_suite_base.hooks.branding.email_template_updater import update_email_templates
        update_email_templates(env)
        _logger.info("✓ Email templates customized")

        # Step 9: Configure mail server
        _logger.info("[8/9] Configuring mail server...")
        from odoo.addons.via_suite_base.hooks.mail_config import configure_mail_server
        mail_ok = configure_mail_server(env)
        if mail_ok:
            _logger.info("✓ Mail server configured from environment variables")
        else:
            _logger.warning("✗ Failed to configure mail server")

        # Step 9: Apply company defaults
        _logger.info("[9/9] Applying company defaults...")
        company = env['res.company'].search([], limit=1)
        if company:
            company._apply_viasuite_defaults()
            _logger.info(f"✓ Company defaults applied to: {company.name}")
        else:
            _logger.warning("⊘ No company found to apply defaults")

        # Step 10: Configure OAuth
        _logger.info("[10/10] Configuring OAuth...")
        from odoo.addons.via_suite_base.hooks.oauth_config import configure_oauth
        oauth_ok = configure_oauth(env)
        if oauth_ok:
            _logger.info("✓ OAuth provider configured from environment variables")
        else:
            _logger.warning("✗ Failed to configure OAuth provider")

        # Commit changes
        cr.commit()

        _logger.info("="*80)
        _logger.info("✓ ViaSuite Base installation complete!")
        _logger.info("="*80)
        _logger.info("")
        _logger.info("Next steps:")
        _logger.info("1. Configure Keycloak OAuth provider")
        _logger.info("2. Set up S3 storage backend")
        _logger.info("3. Configure Amazon SES email server")
        _logger.info("4. Add user tenants in Keycloak (via_suite_tenants attribute)")
        _logger.info("")
        _logger.info("For detailed documentation, see README.md")
        _logger.info("="*80)

    except Exception as e:
        _logger.error("="*80)
        _logger.error("✗ Error during ViaSuite Base installation!")
        _logger.error(f"Error: {str(e)}")
        _logger.error("="*80)

        # Try to capture error in Sentry if available
        try:
            from odoo.addons.via_suite_base.hooks.sentry_init import SentryInitializer
            SentryInitializer.capture_exception(
                e,
                context={'phase': 'post_init_hook'}
            )
        except Exception:
            pass

        raise