# -*- coding: utf-8 -*-
"""
Logo Updater
============

Updates default logos with ViaSuite branding.
"""

import os
import base64
import logging

_logger = logging.getLogger(__name__)


class LogoUpdater:
    """
    Updates system logos with ViaSuite branding.

    Updates:
    - Company logo
    - Web interface logo
    - Email template logos
    """

    @classmethod
    def _get_logo_path(cls, logo_name):
        """
        Get the file path for a logo.

        Args:
            logo_name (str): Name of the logo file

        Returns:
            str: Full path to logo file
        """
        module_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        logo_path = os.path.join(
            module_path,
            'static',
            'src',
            'img',
            logo_name
        )
        return logo_path

    @classmethod
    def _load_logo_base64(cls, logo_name):
        """
        Load a logo file and convert to base64.

        Args:
            logo_name (str): Name of the logo file

        Returns:
            str: Base64 encoded logo data, or None if file not found
        """
        try:
            logo_path = cls._get_logo_path(logo_name)

            if not os.path.exists(logo_path):
                _logger.warning(f"Logo file not found: {logo_path}")
                return None

            with open(logo_path, 'rb') as f:
                logo_data = f.read()

            return base64.b64encode(logo_data).decode('utf-8')

        except Exception as e:
            _logger.error(f"Error loading logo {logo_name}: {str(e)}")
            return None

    @classmethod
    def update_company_logo(cls, env):
        """
        Update the default company logo with ViaSuite logo.

        Args:
            env: Odoo environment
        """
        try:
            # Load ViaSuite logo
            logo_base64 = cls._load_logo_base64('company_default.png')

            if not logo_base64:
                _logger.warning("Could not load ViaSuite company logo")
                return

            # Update all companies
            companies = env['res.company'].search([])

            for company in companies:
                # Only update if company has no logo or default Odoo logo
                if not company.logo or cls._is_default_odoo_logo(company.logo):
                    company.write({'logo': logo_base64})

            _logger.info(f"Updated logo for {len(companies)} companies")

        except Exception as e:
            _logger.error(f"Error updating company logo: {str(e)}")

    @classmethod
    def _is_default_odoo_logo(cls, logo_data):
        """
        Check if the logo is the default Odoo logo.

        Args:
            logo_data (bytes): Logo image data

        Returns:
            bool: True if it's the default Odoo logo
        """
        # Simple heuristic: default Odoo logo is relatively small
        # This is a simplified check - in production you might want
        # to compare actual image hashes
        if not logo_data:
            return True

        try:
            # Decode base64 if needed
            if isinstance(logo_data, str):
                logo_data = base64.b64decode(logo_data)

            # Default Odoo logo is typically < 5KB
            return len(logo_data) < 5000

        except Exception:
            return False

    @classmethod
    def update_web_logos(cls, env):
        """
        Update web interface logos.

        This updates logo references in web templates.

        Args:
            env: Odoo environment
        """
        try:
            # The web logos are updated via webclient_templates.xml
            # This method can be extended if dynamic updates are needed

            _logger.info("Web logos configured via templates")

        except Exception as e:
            _logger.error(f"Error updating web logos: {str(e)}")

    @classmethod
    def update_all_logos(cls, env):
        """
        Update all system logos with ViaSuite branding.

        Args:
            env: Odoo environment
        """
        _logger.info("Starting ViaSuite logo updates...")

        cls.update_company_logo(env)
        cls.update_web_logos(env)

        _logger.info("ViaSuite logo updates complete")


def update_logos(env):
    """
    Convenience function to update all logos.

    Args:
        env: Odoo environment
    """
    LogoUpdater.update_all_logos(env)