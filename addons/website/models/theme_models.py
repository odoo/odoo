# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, modules
from odoo.tools.translate import xml_translate
from odoo.modules.module import get_resource_from_path

from odoo.addons.base.models.ir_asset import DEFAULT_SEQUENCE


class ThemeIrUiView(models.Model):
    _name = 'theme.ir.ui.view'
    _description = 'Theme UI View'

    def compute_arch_fs(self):
        if 'install_filename' not in self.env.context:
            return ''
        path_info = get_resource_from_path(self.env.context['install_filename'])
        if path_info:
            return '/'.join(path_info[0:2])

    name = fields.Char(required=True)
    key = fields.Char()
    type = fields.Char()
    priority = fields.Integer(default=DEFAULT_SEQUENCE, required=True)
    mode = fields.Selection([('primary', "Base view"), ('extension', "Extension View")])
    active = fields.Boolean(default=True)
    arch = fields.Text(translate=xml_translate)
    arch_fs = fields.Char(default=compute_arch_fs)
    inherit_id = fields.Reference(selection=[('ir.ui.view', 'ir.ui.view'), ('theme.ir.ui.view', 'theme.ir.ui.view')])
    copy_ids = fields.One2many('ir.ui.view', 'theme_template_id', 'Views using a copy of me', copy=False, readonly=True)
    customize_show = fields.Boolean()

    def _convert_to_base_model(self, website, **kwargs):
        self.ensure_one()
        inherit = self.inherit_id
        if self.inherit_id and self.inherit_id._name == 'theme.ir.ui.view':
            inherit = self.inherit_id.with_context(active_test=False).copy_ids.filtered(lambda x: x.website_id == website)
            if not inherit:
                # inherit_id not yet created, add to the queue
                return False

        if inherit and inherit.website_id != website:
            website_specific_inherit = self.env['ir.ui.view'].with_context(active_test=False).search([
                ('key', '=', inherit.key),
                ('website_id', '=', website.id)
            ], limit=1)
            if website_specific_inherit:
                inherit = website_specific_inherit

        new_view = {
            'type': self.type or 'qweb',
            'name': self.name,
            'arch': self.arch,
            'key': self.key,
            'inherit_id': inherit and inherit.id,
            'arch_fs': self.arch_fs,
            'priority': self.priority,
            'active': self.active,
            'theme_template_id': self.id,
            'website_id': website.id,
            'customize_show': self.customize_show,
        }

        if self.mode:  # if not provided, it will be computed automatically (if inherit_id or not)
            new_view['mode'] = self.mode

        return new_view


class ThemeIrAttachment(models.Model):
    _name = 'theme.ir.attachment'
    _description = 'Theme Attachment'

    name = fields.Char(required=True)
    key = fields.Char(required=True)
    url = fields.Char()
    copy_ids = fields.One2many('ir.attachment', 'theme_template_id', 'Attachment using a copy of me', copy=False, readonly=True)

    def _convert_to_base_model(self, website, **kwargs):
        self.ensure_one()
        new_attach = {
            'key': self.key,
            'public': True,
            'res_model': 'ir.ui.view',
            'type': 'url',
            'name': self.name,
            'url': self.url,
            'website_id': website.id,
            'theme_template_id': self.id,
        }
        return new_attach


class WebsiteThemeMixin(models.AbstractModel):
    _name = 'website.theme.mixin'
    _description = 'Record installed by a website theme'

    theme_id = fields.Many2one('ir.module.module', index='btree_not_null')

    def _load_records(self, data_list, update=False):
        # The records of a theme module belong to that theme
        theme_category = self.env.ref('base.module_category_theme')
        for data in data_list:
            module = self.env['ir.module.module']._get((data.get('xml_id') or '').split('.')[0])
            if theme_category in (module.category_id, module.category_id.parent_id):
                data['values']['theme_id'] = module.id
        return super()._load_records(data_list, update)


class IrUiView(models.Model):
    _name = 'ir.ui.view'
    _inherit = ['ir.ui.view', 'website.theme.mixin']

    theme_template_id = fields.Many2one('theme.ir.ui.view', copy=False, index='btree_not_null')

    def write(self, vals):
        # During a theme module update, theme views' copies receiving an arch
        # update should not be considered as `arch_updated`, as this is not a
        # user made change.
        test_mode = modules.module.current_test
        if not (test_mode or not self.pool.ready):
            return super().write(vals)
        no_arch_updated_views = other_views = self.env['ir.ui.view']
        for record in self:
            # Do not mark the view as user updated if original view arch is similar
            arch = vals.get('arch', vals.get('arch_base'))
            if record.theme_template_id and record.theme_template_id.arch == arch:
                no_arch_updated_views += record
            else:
                other_views += record
        res = super(IrUiView, other_views).write(vals)
        if no_arch_updated_views:
            vals['arch_updated'] = False
            res &= super(IrUiView, no_arch_updated_views).write(vals)
        return res


class IrAsset(models.Model):
    _name = 'ir.asset'
    _inherit = ['ir.asset', 'website.theme.mixin']


class IrAttachment(models.Model):
    _name = 'ir.attachment'
    _inherit = ['ir.attachment', 'website.theme.mixin']

    key = fields.Char(copy=False)
    theme_template_id = fields.Many2one('theme.ir.attachment', copy=False, index='btree_not_null')
