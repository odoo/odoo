# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.base.models.ir_asset import AssetPaths

# Needed in each bundle to compile its scss.
SCSS_VARIABLES = {
    '/web/static/src/scss/pre_variables.scss',
    '/web/static/lib/bootstrap/scss/_variables.scss',
    '/web/static/lib/bootstrap/scss/_variables-dark.scss',
    '/web/static/lib/bootstrap/scss/_maps.scss',
}


class LazyFrontendBundleCase(TransactionCase):

    def assertNotInFrontend(self, bundle, allowed=()):
        """Assert the files of a lazy bundle are not already in the frontend.

        The bundle and the frontend are built with the bundle's module and its
        dependencies only: other modules may add the same files to the frontend,
        but the lazy bundle can't rely on them.

        :param allowed: paths that the bundle needs even if they are in the frontend
        """
        IrAsset = self.env['ir.asset']
        installed = IrAsset._get_installed_addons_list()
        module = self.env['ir.module.module'].search([('name', '=', bundle.split('.')[0])])
        dependencies = module.upstream_dependencies(exclude_states=()).mapped('name')
        addons = IrAsset._topological_sort((module.name, *dependencies))

        def get_paths(bundle):
            asset_paths = AssetPaths()
            IrAsset._fill_asset_paths(bundle, asset_paths, [], addons, installed)
            return {path for path, *_ in asset_paths.list}

        helpers = get_paths('web._assets_helpers') | get_paths('web._assets_frontend_helpers')
        self.assertFalse(
            get_paths(bundle) & get_paths('web.assets_frontend') - helpers - SCSS_VARIABLES - set(allowed),
            f"these files are loaded twice in the frontend: remove them from {bundle}",
        )


@tagged('post_install', '-at_install')
class TestAssets(LazyFrontendBundleCase):

    def test_assets_editor_frontend_not_in_frontend(self):
        self.assertNotInFrontend('html_editor.assets_editor_frontend')
