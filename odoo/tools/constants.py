# Part of Odoo. See LICENSE file for full copyright and licensing details.

SCRIPT_EXTENSIONS = ('js',)
STYLE_EXTENSIONS = ('css', 'scss', 'sass', 'less')
TEMPLATE_EXTENSIONS = ('xml',)
ASSET_EXTENSIONS = SCRIPT_EXTENSIONS + STYLE_EXTENSIONS + TEMPLATE_EXTENSIONS

SUPPORTED_DEBUGGER = {'pdb', 'ipdb', 'wdb', 'pudb'}
EXTERNAL_ASSET = object()

PREFETCH_MAX = 1000
"""Maximum number of prefetched records"""

GC_UNLINK_LIMIT = 100_000
"""Maximuum number of records to clean in a single transaction."""
