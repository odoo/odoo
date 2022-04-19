# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import threading
from odoo import api, fields, models
from odoo.tools.translate import xml_translate
from odoo.modules.module import get_resource_from_path

from odoo.addons.base.models.ir_asset import AFTER_DIRECTIVE, APPEND_DIRECTIVE, BEFORE_DIRECTIVE, DEFAULT_SEQUENCE, INCLUDE_DIRECTIVE, PREPEND_DIRECTIVE, REMOVE_DIRECTIVE, REPLACE_DIRECTIVE

_logger = logging.getLogger(__name__)


class ThemeAsset(models.Model):
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


class ThemeView(models.Model):
    _name = 'theme.ir.ui.view'
    _description = 'Theme UI View'

    def compute_arch_fs(self):
        if 'install_filename' not in self._context:
            return ''
        path_info = get_resource_from_path(self._context['install_filename'])
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


class ThemeAttachment(models.Model):
    _name = 'theme.ir.attachment'
    _description = 'Theme Attachments'

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


class ThemeMenu(models.Model):
    _name = 'theme.website.menu'
    _description = 'Website Theme Menu'

    name = fields.Char(required=True, translate=True)
    url = fields.Char(default='')
    page_id = fields.Many2one('theme.website.page', ondelete='cascade')
    new_window = fields.Boolean('New Window')
    sequence = fields.Integer()
    parent_id = fields.Many2one('theme.website.menu', index=True, ondelete="cascade")
    copy_ids = fields.One2many('website.menu', 'theme_template_id', 'Menu using a copy of me', copy=False, readonly=True)

    def _convert_to_base_model(self, website, **kwargs):
        self.ensure_one()
        page_id = self.page_id.copy_ids.filtered(lambda x: x.website_id == website)
        parent_id = self.copy_ids.filtered(lambda x: x.website_id == website)
        new_menu = {
            'name': self.name,
            'url': self.url,
            'page_id': page_id and page_id.id or False,
            'new_window': self.new_window,
            'sequence': self.sequence,
            'parent_id': parent_id and parent_id.id or False,
            'theme_template_id': self.id,
        }
        return new_menu


class ThemePage(models.Model):
    _name = 'theme.website.page'
    _description = 'Website Theme Page'

    url = fields.Char()
    view_id = fields.Many2one('theme.ir.ui.view', required=True, ondelete="cascade")
    website_indexed = fields.Boolean('Page Indexed', default=True)
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
            'theme_template_id': self.id,
        }
        return new_page


class Theme(models.AbstractModel):
    _name = 'theme.utils'
    _description = 'Theme Utils'
    _auto = False

    _header_templates = [
        'website.template_header_hamburger',
        'website.template_header_vertical',
        'website.template_header_sidebar',
        'website.template_header_slogan',
        'website.template_header_contact',
        'website.template_header_boxed',
        'website.template_header_centered_logo',
        'website.template_header_image',
        'website.template_header_hamburger_full',
        'website.template_header_magazine',
        # Default one, keep it last
        'website.template_header_default',
    ]
    _footer_templates = [
        'website.template_footer_descriptive',
        'website.template_footer_centered',
        'website.template_footer_links',
        'website.template_footer_minimalist',
        'website.template_footer_contact',
        'website.template_footer_call_to_action',
        'website.template_footer_headline',
        # Default one, keep it last
        'website.footer_custom',
    ]

    def _post_copy(self, mod):
        # Call specific theme post copy
        theme_post_copy = '_%s_post_copy' % mod.name
        if hasattr(self, theme_post_copy):
            _logger.info('Executing method %s' % theme_post_copy)
            method = getattr(self, theme_post_copy)
            return method(mod)
        return False

    @api.model
    def _reset_default_config(self):
        # Reinitialize some css customizations
        self.env['web_editor.assets'].make_scss_customization(
            '/website/static/src/scss/options/user_values.scss',
            {
                'font': 'null',
                'headings-font': 'null',
                'navbar-font': 'null',
                'buttons-font': 'null',
                'color-palettes-number': 'null',
                'color-palettes-name': 'null',
                'btn-ripple': 'null',
                'header-template': 'null',
                'footer-template': 'null',
                'footer-scrolltop': 'null',
            }
        )

        # Reinitialize effets
        self.disable_asset('Ripple effect SCSS')
        self.disable_asset('Ripple effect JS')

        # Reinitialize header templates
        for view in self._header_templates[:-1]:
            self.disable_view(view)
        self.enable_view(self._header_templates[-1])

        # Reinitialize footer templates
        for view in self._footer_templates[:-1]:
            self.disable_view(view)
        self.enable_view(self._footer_templates[-1])

        # Reinitialize footer scrolltop template
        self.disable_view('website.option_footer_scrolltop')

    # TODO Rename name in key and search with the key in master
    @api.model
    def _toggle_asset(self, name, active):
        ThemeAsset = self.env['theme.ir.asset'].sudo().with_context(active_test=False)
        obj = ThemeAsset.search([('name', '=', name)])
        website = self.env['website'].get_current_website()
        if obj:
            obj = obj.copy_ids.filtered(lambda x: x.website_id == website)
        else:
            Asset = self.env['ir.asset'].sudo().with_context(active_test=False)
            obj = Asset.search([('name', '=', name)], limit=1)
            has_specific = obj.key and Asset.search_count([
                ('key', '=', obj.key),
                ('website_id', '=', website.id)
            ]) >= 1
            if not has_specific and active == obj.active:
                return
        obj.write({'active': active})

    @api.model
    def _toggle_view(self, xml_id, active):
        obj = self.env.ref(xml_id)
        website = self.env['website'].get_current_website()
        if obj._name == 'theme.ir.ui.view':
            obj = obj.with_context(active_test=False)
            obj = obj.copy_ids.filtered(lambda x: x.website_id == website)
        else:
            # If a theme post copy wants to enable/disable a view, this is to
            # enable/disable a given functionality which is disabled/enabled
            # by default. So if a post copy asks to enable/disable a view which
            # is already enabled/disabled, we would not consider it otherwise it
            # would COW the view for nothing.
            View = self.env['ir.ui.view'].with_context(active_test=False)
            has_specific = obj.key and View.search_count([
                ('key', '=', obj.key),
                ('website_id', '=', website.id)
            ]) >= 1
            if not has_specific and active == obj.active:
                return
        obj.write({'active': active})

    @api.model
    def enable_asset(self, name):
        self._toggle_asset(name, True)

    @api.model
    def disable_asset(self, name):
        self._toggle_asset(name, False)

    @api.model
    def enable_view(self, xml_id):
        if xml_id in self._header_templates:
            for view in self._header_templates:
                self.disable_view(view)
        elif xml_id in self._footer_templates:
            for view in self._footer_templates:
                self.disable_view(view)
        self._toggle_view(xml_id, True)

    @api.model
    def disable_view(self, xml_id):
        self._toggle_view(xml_id, False)

    @api.model
    def enable_header_off_canvas(self):
        """ Enabling off canvas require to enable quite a lot of template so
            this shortcut was made to make it easier.
        """
        self.enable_view("website.option_header_off_canvas")
        self.enable_view("website.option_header_off_canvas_template_header_hamburger")
        self.enable_view("website.option_header_off_canvas_template_header_sidebar")
        self.enable_view("website.option_header_off_canvas_template_header_hamburger_full")


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    theme_template_id = fields.Many2one('theme.ir.ui.view', copy=False)

    def write(self, vals):
        # During a theme module update, theme views' copies receiving an arch
        # update should not be considered as `arch_updated`, as this is not a
        # user made change.
        test_mode = getattr(threading.currentThread(), 'testing', False)
        if not (test_mode or self.pool._init):
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

    theme_template_id = fields.Many2one('theme.ir.asset', copy=False)

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    key = fields.Char(copy=False)
    theme_template_id = fields.Many2one('theme.ir.attachment', copy=False)


class WebsiteMenu(models.Model):
    _inherit = 'website.menu'

    theme_template_id = fields.Many2one('theme.website.menu', copy=False)


class WebsitePage(models.Model):
    _inherit = 'website.page'

    theme_template_id = fields.Many2one('theme.website.page', copy=False)
