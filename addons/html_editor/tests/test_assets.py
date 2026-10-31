# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestAssets(TransactionCase):

    def test_assets_editor_frontend_not_in_frontend(self):
        IrAsset = self.env['ir.asset']
        params = IrAsset._get_asset_params()

        def get_paths(bundle):
            return {path for path, *_ in IrAsset._get_asset_paths(bundle, params)}

        frontend = get_paths('web.assets_frontend') | get_paths('web.assets_frontend_minimal')
        editor = get_paths('html_editor.assets_editor_frontend')
        # It's okay to have duplicate scss helpers and variables, as they are
        # needed to compile the bundle.
        helpers = get_paths('web._assets_helpers') | get_paths('web._assets_frontend_helpers')
        duplicated = {path for path in editor & frontend - helpers if not path.startswith('/web/')}
        self.assertFalse(
            duplicated,
            "these files are loaded twice in the frontend: remove them from "
            "html_editor.assets_editor_frontend",
        )
