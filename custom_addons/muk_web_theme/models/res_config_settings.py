from __future__ import annotations

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Manage the backend theme favicon, background image, and colors."""

    _inherit = 'res.config.settings'

    @property
    def THEME_COLOR_FIELDS(self) -> list[str]:
        """Return the theme color variable field names."""
        return [
            'color_appsmenu_text',
            'color_appbar_text',
            'color_appbar_active',
            'color_appbar_background',
        ]

    @property
    def COLOR_ASSET_THEME_URL(self) -> str:
        """Return the SCSS asset URL holding the theme color variables."""
        return '/muk_web_theme/static/src/scss/colors.scss'

    @property
    def COLOR_BUNDLE_THEME_NAME(self) -> str:
        """Return the asset bundle name holding the theme color variables."""
        return 'web._assets_primary_variables'

    # ----------------------------------------------------------
    # Fields
    # ----------------------------------------------------------

    theme_favicon = fields.Binary(
        related='company_id.favicon',
        readonly=False,
    )

    theme_background_image = fields.Binary(
        related='company_id.background_image',
        readonly=False,
    )

    theme_color_appsmenu_text = fields.Char(
        string='Apps Menu Text Color',
    )

    theme_color_appbar_text = fields.Char(
        string='AppsBar Text Color',
    )

    theme_color_appbar_active = fields.Char(
        string='AppsBar Active Color',
    )

    theme_color_appbar_background = fields.Char(
        string='AppsBar Background Color',
    )

    # ----------------------------------------------------------
    # Helper
    # ----------------------------------------------------------

    def _get_theme_color_values(self) -> dict:
        """Read the current theme color variable values from the asset."""
        return self.env[
            'muk_web_colors.color_assets_editor'
        ].get_color_variables_values(
            self.COLOR_ASSET_THEME_URL,
            self.COLOR_BUNDLE_THEME_NAME,
            self.THEME_COLOR_FIELDS,
        )

    def _set_theme_color_values(self, values: dict) -> dict:
        """Inject the current theme color values into ``values``."""
        colors = self._get_theme_color_values()
        for var, value in colors.items():
            values[f'theme_{var}'] = value
        return values

    def _detect_theme_color_change(self) -> bool:
        """Return whether any theme color field differs from the asset."""
        colors = self._get_theme_color_values()
        return any(self[f'theme_{var}'] != val for var, val in colors.items())

    def _replace_theme_color_values(self):
        """Write the theme color fields back into the asset."""
        variables = [
            {
                'name': field,
                'value': self[f'theme_{field}'],
            }
            for field in self.THEME_COLOR_FIELDS
        ]
        return self.env[
            'muk_web_colors.color_assets_editor'
        ].replace_color_variables_values(
            self.COLOR_ASSET_THEME_URL,
            self.COLOR_BUNDLE_THEME_NAME,
            variables,
        )

    def _reset_theme_color_assets(self) -> None:
        """Reset the theme color asset to its default content."""
        self.env['muk_web_colors.color_assets_editor'].reset_color_asset(
            self.COLOR_ASSET_THEME_URL,
            self.COLOR_BUNDLE_THEME_NAME,
        )

    # ----------------------------------------------------------
    # Action
    # ----------------------------------------------------------

    def action_reset_theme_color_assets(self) -> dict:
        """Reset light, dark, and theme color assets, then reload the client."""
        self._reset_light_color_assets()
        self._reset_dark_color_assets()
        self._reset_theme_color_assets()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    # ----------------------------------------------------------
    # Functions
    # ----------------------------------------------------------

    def get_values(self) -> dict:
        """Extend the settings values with the theme color values."""
        res = super().get_values()
        return self._set_theme_color_values(res)

    def set_values(self) -> dict:
        """Persist the settings and write back changed theme colors."""
        res = super().set_values()
        if self._detect_theme_color_change():
            self._replace_theme_color_values()
        return res
