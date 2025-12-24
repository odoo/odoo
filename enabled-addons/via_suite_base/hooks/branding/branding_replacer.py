# -*- coding: utf-8 -*-
"""
Branding String Replacer
=========================

Replaces Odoo branding strings with ViaSuite branding throughout the system.
"""

import logging

_logger = logging.getLogger(__name__)


class BrandingReplacer:
    """
    Replaces Odoo branding with ViaSuite branding.

    Replaces strings in:
    - UI views
    - Menu items
    - Translations
    - System parameters
    """

    # Mapping of strings to replace
    REPLACEMENTS = {
        'Odoo': 'ViaSuite',
        'odoo': 'viasuite',
        'Odoo S.A.': 'ViaFronteira, LLC',
        'www.odoo.com': 'www.viafronteira.com',
        'odoo.com': 'viafronteira.com',
    }

    @classmethod
    def replace_in_views(cls, env):
        """
        Replace branding strings in ir.ui.view.

        Args:
            env: Odoo environment

        Returns:
            int: Number of views updated
        """
        try:
            views = env['ir.ui.view'].search([])
            updated_count = 0

            for view in views:
                if not view.arch_db:
                    continue

                arch = view.arch_db
                modified = False

                for old_str, new_str in cls.REPLACEMENTS.items():
                    if old_str in arch:
                        arch = arch.replace(old_str, new_str)
                        modified = True

                if modified:
                    try:
                        view.write({'arch_db': arch})
                        updated_count += 1
                    except Exception as e:
                        _logger.warning(
                            f"Failed to update view {view.name}: {str(e)}"
                        )

            _logger.info(f"Updated branding in {updated_count} views")
            return updated_count

        except Exception as e:
            _logger.error(f"Error replacing branding in views: {str(e)}")
            return 0

    @classmethod
    def replace_in_menus(cls, env):
        """
        Replace branding strings in ir.ui.menu.

        Args:
            env: Odoo environment

        Returns:
            int: Number of menus updated
        """
        try:
            menus = env['ir.ui.menu'].search([])
            updated_count = 0

            for menu in menus:
                modified = False
                new_name = menu.name

                for old_str, new_str in cls.REPLACEMENTS.items():
                    if old_str in new_name:
                        new_name = new_name.replace(old_str, new_str)
                        modified = True

                if modified:
                    try:
                        menu.write({'name': new_name})
                        updated_count += 1
                    except Exception as e:
                        _logger.warning(
                            f"Failed to update menu {menu.name}: {str(e)}"
                        )

            _logger.info(f"Updated branding in {updated_count} menus")
            return updated_count

        except Exception as e:
            _logger.error(f"Error replacing branding in menus: {str(e)}")
            return 0

    @classmethod
    def replace_in_translations(cls, env):
        """
        Replace branding strings in ir.translation.

        Args:
            env: Odoo environment

        Returns:
            int: Number of translations updated
        """
        try:
            translations = env['ir.translation'].search([])
            updated_count = 0

            for translation in translations:
                if not translation.value:
                    continue

                modified = False
                new_value = translation.value

                for old_str, new_str in cls.REPLACEMENTS.items():
                    if old_str in new_value:
                        new_value = new_value.replace(old_str, new_str)
                        modified = True

                if modified:
                    try:
                        translation.write({'value': new_value})
                        updated_count += 1
                    except Exception as e:
                        _logger.warning(
                            f"Failed to update translation: {str(e)}"
                        )

            _logger.info(f"Updated branding in {updated_count} translations")
            return updated_count

        except Exception as e:
            _logger.error(f"Error replacing branding in translations: {str(e)}")
            return 0

    @classmethod
    def replace_in_ir_config_parameters(cls, env):
        """
        Update system parameters with ViaSuite branding.

        Args:
            env: Odoo environment
        """
        try:
            params_to_update = {
                'web.base.url.freeze': False,  # Allow custom base URL
            }

            for key, value in params_to_update.items():
                env['ir.config_parameter'].sudo().set_param(key, value)

            _logger.info("Updated system parameters with ViaSuite branding")

        except Exception as e:
            _logger.error(f"Error updating system parameters: {str(e)}")

    @classmethod
    def apply_all_replacements(cls, env):
        """
        Apply all branding replacements.

        Args:
            env: Odoo environment

        Returns:
            dict: Statistics about replacements
        """
        _logger.info("Starting ViaSuite branding replacements...")

        stats = {
            'views': cls.replace_in_views(env),
            'menus': cls.replace_in_menus(env),
            'translations': cls.replace_in_translations(env),
        }

        cls.replace_in_ir_config_parameters(env)

        _logger.info(
            f"ViaSuite branding complete: {stats['views']} views, "
            f"{stats['menus']} menus, {stats['translations']} translations updated"
        )

        return stats


def apply_branding_replacements(env):
    """
    Convenience function to apply all branding replacements.

    Args:
        env: Odoo environment

    Returns:
        dict: Statistics about replacements
    """
    return BrandingReplacer.apply_all_replacements(env)