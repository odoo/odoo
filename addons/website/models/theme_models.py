# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class WebsiteThemeMixin(models.AbstractModel):
    _name = 'website.theme.mixin'
    _description = 'Record installed by a website theme'

    theme_id = fields.Many2one('ir.module.module', index='btree_not_null')

    # Values the records of a theme get when they are loaded, unless the theme sets them
    _theme_defaults = {}

    def _load_records(self, data_list, update=False):
        # The records of a theme module belong to that theme
        theme_category = self.env.ref('base.module_category_theme')
        for data in data_list:
            module = self.env['ir.module.module']._get((data.get('xml_id') or '').split('.')[0])
            if theme_category in (module.category_id, module.category_id.parent_id):
                data['values'] = {**self._theme_defaults, **data['values'], 'theme_id': module.id}
        return super()._load_records(data_list, update)


class IrUiView(models.Model):
    _name = 'ir.ui.view'
    _inherit = ['ir.ui.view', 'website.theme.mixin']


class IrAsset(models.Model):
    _name = 'ir.asset'
    _inherit = ['ir.asset', 'website.theme.mixin']


class IrAttachment(models.Model):
    _name = 'ir.attachment'
    _inherit = ['ir.attachment', 'website.theme.mixin']
    # Theme images are served from their url, to every visitor
    _theme_defaults = {'type': 'url', 'public': True, 'res_model': 'ir.ui.view'}

    key = fields.Char(copy=False)
