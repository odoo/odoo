# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

SCRIPT_EXTENSIONS = ('js',)
STYLE_EXTENSIONS = ('css', 'scss', 'sass', 'less')
TEMPLATE_EXTENSIONS = ('xml',)
ASSET_EXTENSIONS = SCRIPT_EXTENSIONS + STYLE_EXTENSIONS + TEMPLATE_EXTENSIONS

SUPPORTED_DEBUGGER = {'pdb', 'ipdb', 'wdb', 'pudb'}
EXTERNAL_ASSET = object()
