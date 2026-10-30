# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, modules
from odoo.tools.translate import xml_translate
from odoo.modules.module import get_resource_from_path

from odoo.addons.base.models.ir_asset import AFTER_DIRECTIVE, APPEND_DIRECTIVE, BEFORE_DIRECTIVE, DEFAULT_SEQUENCE, INCLUDE_DIRECTIVE, PREPEND_DIRECTIVE, REMOVE_DIRECTIVE, REPLACE_DIRECTIVE


class ThemeIrAsset(models.Model):
    _name = 'theme.ir.asset'
    _description = 'Theme Asset'

    key = fields.Char()
    name = fields.Char(required=True)
    bundle = fields.Char(required=True)
    directive = fields.Selection(selection=[
        (APPEND_DIRECTIVE, 'Append'),
        (PREPEND_DIRECTIVE, 'Prepend'),
        (AFTER_DIRECTIVE, 'After'),
        (BEFORE_DIRECTIVE, 'Before'),
        (REMOVE_DIRECTIVE, 'Remove'),
        (REPLACE_DIRECTIVE, 'Replace'),
        (INCLUDE_DIRECTIVE, 'Include')], default=APPEND_DIRECTIVE)
    path = fields.Char(required=True)
    target = fields.Char()
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=DEFAULT_SEQUENCE, required=True)
    copy_ids = fields.One2many('ir.asset', 'theme_template_id', 'Assets using a copy of me', copy=False, readonly=True)

    def _convert_to_base_model(self, website, **kwargs):
        self.ensure_one()
        new_asset = {
            'name': self.name,
            'key': self.key,
            'bundle': self.bundle,
            'directive': self.directive,
            'path': self.path,
            'target': self.target,
            'active': self.active,
            'sequence': self.sequence,
            'website_id': website.id,
            'theme_template_id': self.id,
        }
        return new_asset


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


class ThemeWebsiteMenu(models.Model):
    _name = 'theme.website.menu'
    _description = 'Website Theme Menu'

    name = fields.Char(required=True, translate=True, copy=True)
    url = fields.Char(default='#')
    page_id = fields.Many2one('theme.website.page', ondelete='cascade', index='btree_not_null')
    new_window = fields.Boolean('New Window')
    sequence = fields.Integer()
    parent_id = fields.Many2one('theme.website.menu', index=True, ondelete="cascade")
    mega_menu_content = fields.Html()
    mega_menu_classes = fields.Char()

    use_main_menu_as_parent = fields.Boolean(default=True)
    copy_ids = fields.One2many('website.menu', 'theme_template_id', 'Menu using a copy of me', copy=False, readonly=True)

    def _convert_to_base_model(self, website, **kwargs):
        self.ensure_one()
        page_id = self.page_id.copy_ids.filtered(lambda x: x.website_id == website)

        parent_id = False
        if self.parent_id:
            parent_id = self.parent_id.copy_ids.filtered(lambda x: x.website_id == website)
        elif self.use_main_menu_as_parent:
            parent_id = website.menu_id

        new_menu = {
            'name': self.name,
            'url': self.url,
            'page_id': page_id and page_id.id or False,
            'new_window': self.new_window,
            'sequence': self.sequence,
            'parent_id': parent_id and parent_id.id or False,
            'website_id': website.id,
            'mega_menu_content': self.mega_menu_content,
            'mega_menu_classes': self.mega_menu_classes,
            'theme_template_id': self.id,
        }
        return new_menu


class ThemeWebsitePage(models.Model):
    _name = 'theme.website.page'
    _description = 'Website Theme Page'
    _inherit = [
        'website.page_options.mixin',
    ]

    url = fields.Char(translate=True)
    view_id = fields.Many2one('theme.ir.ui.view', required=True, index=True, ondelete="cascade")
    website_indexed = fields.Boolean('Page Indexed', default=True)
    is_published = fields.Boolean()
    is_new_page_template = fields.Boolean(string="New Page Template")

    copy_ids = fields.One2many('website.page', 'theme_template_id', 'Page using a copy of me', copy=False, readonly=True)

    def _convert_to_base_model(self, website, **kwargs):
        self.ensure_one()
        view_id = self.view_id.copy_ids.filtered(lambda x: x.website_id == website)
        if not view_id:
            # inherit_id not yet created, add to the queue
            return False

        new_page = {
            'url': self.url,
            'view_id': view_id.id,
            'website_indexed': self.website_indexed,
            'is_published': self.is_published,
            'is_new_page_template': self.is_new_page_template,
            'header_overlay': self.header_overlay,
            'header_color': self.header_color,
            'header_text_color': self.header_text_color,
            'header_visible': self.header_visible,
            'footer_visible': self.footer_visible,
            'theme_template_id': self.id,
        }
        return new_page


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

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
    _inherit = 'ir.asset'

    theme_template_id = fields.Many2one('theme.ir.asset', copy=False, index='btree_not_null')


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    key = fields.Char(copy=False)
    theme_template_id = fields.Many2one('theme.ir.attachment', copy=False, index='btree_not_null')


class WebsiteMenu(models.Model):
    _inherit = 'website.menu'

    theme_template_id = fields.Many2one('theme.website.menu', copy=False, index='btree_not_null')


class WebsitePage(models.Model):
    _inherit = 'website.page'

    theme_template_id = fields.Many2one('theme.website.page', copy=False, index='btree_not_null')
