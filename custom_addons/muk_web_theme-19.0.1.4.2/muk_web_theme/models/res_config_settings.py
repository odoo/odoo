from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    @property
    def THEME_COLOR_FIELDS(self):
        return [
            'color_appsmenu_text',
            'color_appbar_text',
            'color_appbar_active',
            'color_appbar_background',
        ]

    @property
    def COLOR_ASSET_THEME_URL(self):
        return '/muk_web_theme/static/src/scss/colors.scss'
        
    @property
    def COLOR_BUNDLE_THEME_NAME(self):
        return 'web._assets_primary_variables'
    
    #----------------------------------------------------------
    # Fields
    #----------------------------------------------------------
    
    theme_favicon = fields.Binary(
        related='company_id.favicon',
        readonly=False
    )
    
    theme_background_image = fields.Binary(
        related='company_id.background_image',
        readonly=False
    )
    
    theme_color_appsmenu_text = fields.Char(
        string='Apps Menu Text Color'
    )
    
    theme_color_appbar_text = fields.Char(
        string='AppsBar Text Color'
    )
    
    theme_color_appbar_active = fields.Char(
        string='AppsBar Active Color'
    )
    
    theme_color_appbar_background = fields.Char(
        string='AppsBar Background Color'
    )
    
    #----------------------------------------------------------
    # Helper
    #----------------------------------------------------------
    
    def _get_theme_color_values(self):
        return self.env['muk_web_colors.color_assets_editor'].get_color_variables_values(
            self.COLOR_ASSET_THEME_URL, 
            self.COLOR_BUNDLE_THEME_NAME,
            self.THEME_COLOR_FIELDS
        )
        
    def _set_theme_color_values(self, values):
        colors = self._get_theme_color_values()
        for var, value in colors.items():
            values[f'theme_{var}'] = value
        return values

    def _detect_theme_color_change(self):
        colors = self._get_theme_color_values()
        return any(
            self[f'theme_{var}'] != val
            for var, val in colors.items()
        )

    def _replace_theme_color_values(self):
        variables = [
            {
                'name': field, 
                'value': self[f'theme_{field}']
            }
            for field in self.THEME_COLOR_FIELDS
        ]
        return self.env['muk_web_colors.color_assets_editor'].replace_color_variables_values(
            self.COLOR_ASSET_THEME_URL, 
            self.COLOR_BUNDLE_THEME_NAME,
            variables
        )

    def _reset_theme_color_assets(self):
        self.env['muk_web_colors.color_assets_editor'].reset_color_asset(
            self.COLOR_ASSET_THEME_URL, 
            self.COLOR_BUNDLE_THEME_NAME,
        )
    
    #----------------------------------------------------------
    # Action
    #----------------------------------------------------------
    
    def action_reset_theme_color_assets(self):
        self._reset_light_color_assets()
        self._reset_dark_color_assets()
        self._reset_theme_color_assets()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    #----------------------------------------------------------
    # Functions
    #----------------------------------------------------------

    def get_values(self):
        res = super().get_values()
        res = self._set_theme_color_values(res)
        return res

    def set_values(self):
        res = super().set_values()
        if self._detect_theme_color_change():
            self._replace_theme_color_values()
        return res
