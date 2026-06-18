# Part of Odoo. See LICENSE file for full copyright and licensing details.

SCRIPT_EXTENSIONS = ('js',)
STYLE_EXTENSIONS = ('css', 'scss', 'sass', 'less')
TEMPLATE_EXTENSIONS = ('xml',)
FONT_EXTENSIONS = ('woff', 'woff2')
BINARY_EXTENSIONS = FONT_EXTENSIONS
ASSET_EXTENSIONS = SCRIPT_EXTENSIONS + STYLE_EXTENSIONS + TEMPLATE_EXTENSIONS + BINARY_EXTENSIONS

SUPPORTED_DEBUGGER = {'pdb', 'ipdb', 'wdb', 'pudb'}
EXTERNAL_ASSET = object()

IN_MAX = 1000
"""Maximum number of records in an IN clause"""

BIG_RECORDSET_SIZE = 10_000
"""Maximum number of records in a recordset to consider it as "big" and avoid prefetching"""

GC_UNLINK_LIMIT = 100_000
"""Maximuum number of records to clean in a single transaction."""
