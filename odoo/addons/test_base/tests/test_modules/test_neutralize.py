# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.modules import neutralize
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'neutralize')
class TestNeutralize(TransactionCase):
    def test_10_neutralize(self):
        """ Simply testing that none of the SQL neutralize crashes """
        installed_modules = neutralize.get_installed_modules(self.cr)
        queries = neutralize.get_neutralization_queries(installed_modules)
        for query in queries:
            self.cr.execute(query)

    def test_20_neutralize_dependency_order(self):
        """ Each module comes after the modules it depends on, so that its
        neutralization can refine the neutralization of its dependencies """
        installed_modules = neutralize.get_installed_modules(self.cr)
        self.assertEqual(installed_modules[0], 'base')
        position = {name: index for index, name in enumerate(installed_modules)}
        modules = self.env['ir.module.module'].search([('name', 'in', installed_modules)])
        self.assertEqual(len(modules), len(installed_modules))
        for module in modules:
            for dependency in module.dependencies_id:
                self.assertLess(
                    position[dependency.name], position[module.name],
                    f"{dependency.name} must be neutralized before {module.name}",
                )
