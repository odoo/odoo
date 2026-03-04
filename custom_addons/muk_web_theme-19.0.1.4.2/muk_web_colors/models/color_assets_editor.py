import re
import base64

from odoo import models, fields, api
from odoo.tools import misc

from odoo.addons.base.models.assetsbundle import EXTENSIONS


class ColorAssetsEditor(models.AbstractModel):
    
    _name = 'muk_web_colors.color_assets_editor'
    _description = 'Color Assets Utils'

    # ----------------------------------------------------------
    # Helper
    # ----------------------------------------------------------

    @api.model
    def _get_custom_colors_url(self, url, bundle):
        return f'/_custom/{bundle}{url}'

    @api.model
    def _get_color_info_from_url(self, url):
        regex = re.compile(
            r'^(/_custom/([^/]+))?/(\w+)/([/\w]+\.\w+)$'
        )
        match = regex.match(url)
        if not match:
            return False
        return {
            'module': match.group(3),
            'resource_path': match.group(4),
            'customized': bool(match.group(1)),
            'bundle': match.group(2) or False
        }

    @api.model
    def _get_colors_attachment(self, custom_url):
        return self.env['ir.attachment'].search([
            ('url', '=', custom_url)
        ])

    @api.model
    def _get_colors_asset(self, custom_url):
        return self.env['ir.asset'].search([
            ('path', 'like', custom_url)
        ])

    @api.model
    def _get_colors_from_url(self, url, bundle):
        custom_url = self._get_custom_colors_url(url, bundle)
        url_info = self._get_color_info_from_url(custom_url)
        if url_info['customized']:
            attachment = self._get_colors_attachment(
                custom_url
            )
            if attachment:
                return base64.b64decode(attachment.datas)
        with misc.file_open(url.strip('/'), 'rb', filter_ext=EXTENSIONS) as f:
            return f.read()

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

    @api.model
    def _save_color_asset(self, url, bundle, content):
        custom_url = self._get_custom_colors_url(url, bundle)
        asset_url = url[1:] if url.startswith(('/', '\\')) else url
        datas = base64.b64encode((content or '\n').encode('utf-8'))
        custom_attachment = self._get_colors_attachment(
            custom_url
        )
        if custom_attachment:
            custom_attachment.write({'datas': datas})
            self.env.registry.clear_cache('assets')
        else:
            attachment_values = {
                'name': url.split('/')[-1],
                'type': 'binary',
                'mimetype': 'text/scss',
                'datas': datas,
                'url': custom_url,
            }
            asset_values = {
                'path': custom_url,
                'target': url,
                'directive': 'replace',
            }
            target_asset = self._get_colors_asset(
                asset_url
            )
            if target_asset:
                asset_values['name'] = '%s override' % target_asset.name
                asset_values['bundle'] = target_asset.bundle
                asset_values['sequence'] = target_asset.sequence
            else:
                asset_values['name'] = '%s: replace %s' % (
                    bundle, custom_url.split('/')[-1]
                )
                asset_values['bundle'] = self.env['ir.asset']._get_related_bundle(
                    url, bundle
                )
            self.env['ir.attachment'].create(attachment_values)
            self.env['ir.asset'].create(asset_values)

    # ----------------------------------------------------------
    # Functions
    # ----------------------------------------------------------

    def get_color_variables_values(self, url, bundle, variables):
        content = self._get_colors_from_url(url, bundle)
        return self._get_color_variables(
            content.decode('utf-8'), variables
        )
    
    def replace_color_variables_values(self, url, bundle, variables):
        original = self._get_colors_from_url(url, bundle).decode('utf-8')
        content = self._replace_color_variables(original, variables)
        self._save_color_asset(url, bundle, content)

    def reset_color_asset(self, url, bundle):
        custom_url = self._get_custom_colors_url(url, bundle)
        self._get_colors_attachment(custom_url).unlink()
        self._get_colors_asset(custom_url).unlink()
