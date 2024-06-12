import re

from odoo import models, fields, api


class ScssEditor(models.AbstractModel):
    
    _inherit = 'web_editor.assets'

    # ----------------------------------------------------------
    # Helper
    # ----------------------------------------------------------

    def _get_color_variable(self, content, variable):
        value = re.search(fr'\$mk_{variable}\:?\s(.*?);', content)
        return value and value.group(1)

    def _get_color_variables(self, content, variables):
        return {
            var: self._get_color_variable(content, var) 
            for var in variables
        }

    def _replace_color_variables(self, content, variables):
        for variable in variables:
            content = re.sub(
                fr'{variable["name"]}\:?\s(.*?);', 
                f'{variable["name"]}: {variable["value"]};', 
                content
            )
        return content

    # ----------------------------------------------------------
    # Functions
    # ----------------------------------------------------------

    def get_color_variables_values(self, url, bundle, variables):
        custom_url = self._make_custom_asset_url(url, bundle)
        content = self._get_content_from_url(custom_url)
        if not content:
            content = self._get_content_from_url(url)
        return self._get_color_variables(
            content.decode('utf-8'), variables
        )
    
    def replace_color_variables_values(self, url, bundle, variables):
        original = self._get_content_from_url(url).decode('utf-8')
        content = self._replace_color_variables(original, variables)
        self.with_context(set_color_variables=True).save_asset(
            url, bundle, content, 'scss'
        )
