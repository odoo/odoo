# -*- coding: utf-8 -*-
"""
Theme Injector
==============

Injects ViaSuite color scheme and theme variables into Odoo.

ViaSuite Colors:
- Primary: #FF730E (Orange)
- Secondary: #002147 (Navy Blue)
"""

import logging

_logger = logging.getLogger(__name__)


class ThemeInjector:
    """
    Injects ViaSuite theme and color variables.

    Updates:
    - Company primary color
    - CSS variables (via SCSS files)
    - Web theme settings
    """

    # ViaSuite color palette
    COLORS = {
        'primary': '#FF730E',      # Vibrant orange
        'secondary': '#002147',    # Navy blue
        'success': '#28a745',      # Keep default green
        'info': '#17a2b8',         # Keep default blue
        'warning': '#ffc107',      # Keep default yellow
        'danger': '#dc3545',       # Keep default red
    }

    @classmethod
    def inject_company_colors(cls, env):
        """
        Inject ViaSuite colors into all companies.

        Args:
            env: Odoo environment
        """
        try:
            companies = env['res.company'].search([])

            for company in companies:
                company.write({
                    'primary_color': cls.COLORS['primary'],
                })

            _logger.info(
                f"Injected ViaSuite colors into {len(companies)} companies"
            )

        except Exception as e:
            _logger.error(f"Error injecting company colors: {str(e)}")

    @classmethod
    def update_web_theme_settings(cls, env):
        """
        Update web theme configuration parameters.

        Args:
            env: Odoo environment
        """
        try:
            # Set theme-related configuration parameters
            params = {
                'web.base.url': 'https://viafronteira.app',  # Default, will be overridden by subdomain
            }

            for key, value in params.items():
                env['ir.config_parameter'].sudo().set_param(key, value)

            _logger.info("Updated web theme settings")

        except Exception as e:
            _logger.error(f"Error updating web theme settings: {str(e)}")

    @classmethod
    def inject_all_theme_variables(cls, env):
        """
        Inject all ViaSuite theme variables.

        Args:
            env: Odoo environment
        """
        _logger.info("Starting ViaSuite theme injection...")

        cls.inject_company_colors(env)
        cls.update_web_theme_settings(env)

        _logger.info("ViaSuite theme injection complete")


def inject_theme_variables(env):
    """
    Convenience function to inject theme variables.

    Args:
        env: Odoo environment
    """
    ThemeInjector.inject_all_theme_variables(env)