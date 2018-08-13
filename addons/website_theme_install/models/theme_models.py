# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import fields, models
from odoo.modules.module import get_resource_from_path

_logger = logging.getLogger(__name__)


class ThemeView(models.Model):
    _name = 'theme.ir.ui.view'

    def compute_arch_fs(self):
        path_info = get_resource_from_path(self._context['install_filename'])
        if path_info:
            return '/'.join(path_info[0:2])

    name = fields.Char(required=True)
    key = fields.Char()
    type = fields.Char()
    priority = fields.Integer(default=16, required=True)
    active = fields.Boolean(default=True)
    arch = fields.Text()
    arch_fs = fields.Char(default=compute_arch_fs)
    inherit_id = fields.Reference(selection=[('ir.ui.view', 'ir.ui.view'), ('theme.ir.ui.view', 'theme.ir.ui.view')])
    copy_ids = fields.One2many('ir.ui.view', 'theme_template_id', 'Views using a copy of me', copy=False, readonly=True)


class ThemeAttachment(models.Model):
    _name = 'theme.ir.attachment'

    name = fields.Char(required=True)
    key = fields.Char(required=True)
    url = fields.Char()
    copy_ids = fields.One2many('ir.attachment', 'theme_template_id', 'Attachment using a copy of me', copy=False, readonly=True)


class ThemeMenu(models.Model):
    _name = 'theme.website.menu'

    name = fields.Char(required=True)
    url = fields.Char(default='')
    page_id = fields.Many2one('theme.website.page', ondelete='cascade')
    new_window = fields.Boolean('New Window')
    sequence = fields.Integer()
    parent_id = fields.Many2one('theme.website.menu', index=True, ondelete="cascade")
    copy_ids = fields.One2many('website.menu', 'theme_template_id', 'Menu using a copy of me', copy=False, readonly=True)


class ThemePage(models.Model):
    _name = 'theme.website.page'

    url = fields.Char()
    view_id = fields.Many2one('theme.ir.ui.view', required=True, ondelete="cascade")
    website_indexed = fields.Boolean('Page Indexed', default=True)
    copy_ids = fields.One2many('website.page', 'theme_template_id', 'Theme using a copy of me', copy=False, readonly=True)


class Theme(models.AbstractModel):
    _name = 'theme.utils'
    _auto = False

    def _post_copy(self, mod):
        theme_post_copy = '_%s_post_copy' % mod.name
        if hasattr(self, theme_post_copy):
            _logger.info('Executing method %s' % theme_post_copy)
            method = getattr(self, theme_post_copy)
            return method()


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    theme_template_id = fields.Many2one('theme.ir.ui.view')


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    key = fields.Char()
    theme_template_id = fields.Many2one('theme.ir.attachment')


class WebiteMenu(models.Model):
    _inherit = 'website.menu'

    theme_template_id = fields.Many2one('theme.website.menu')


class WebsitePage(models.Model):
    _inherit = 'website.page'

    theme_template_id = fields.Many2one('theme.website.page')
