import logging

from odoo.tests import tagged

from odoo.addons.populate import start_populate
from odoo.addons.test_populate.tests.common import PopulateTestCase

_logger = logging.getLogger(__name__)


# Main nightly test of the Populate
# run with `populate.test_all_blueprints`
@tagged('populate', '-standard', '-at_install', 'post_install')
class TestAllBlueprint(PopulateTestCase):
    """Run all blueprints 1 by 1."""

    def test_all_blueprints(self):
        blueprints = self.env['populate.blueprint'].search([], order='id')
        self.assertTrue(blueprints, "No blueprints found.")

        for blueprint in blueprints:
            with self.subTest(blueprint=blueprint.name):
                session = self.env['populate.session'].create({
                    'blueprint_id': blueprint.id,
                    'seed': 42,
                })
                _logger.info("Populating %s...", session.blueprint_id.name)
                start_populate(session)

                self.assertTrue(session.is_done, f"Session for '{blueprint.name}' did not complete.")


# Test isn't primordial and takes a bit of time (+-1.5s)
# Can be launch manually with a prefix `populate` test tag,
# e.g. `populate.test_all_sample_blueprints`
@tagged('populate', '-standard')
class TestSampleBlueprints(PopulateTestCase):
    """Run one session per blueprint defined in the test_populate module."""

    def test_all_sample_blueprints(self):
        blueprints = self.env['populate.blueprint'].search([
            ('id', 'in', self.env['ir.model.data'].search([
                ('module', '=', 'test_populate'),
                ('model', '=', 'populate.blueprint'),
            ]).mapped('res_id')),
        ])

        self.assertTrue(blueprints, "No sample blueprints found for module 'test_populate'.")

        for blueprint in blueprints:
            with self.subTest(blueprint=blueprint.name):
                session = self.env['populate.session'].create({
                    'blueprint_id': blueprint.id,
                })
                _logger.info("Populating %s...", session.blueprint_id.name)
                start_populate(session)

                self.assertTrue(
                    session.is_done,
                    msg=f"Session for '{blueprint.name}' did not complete.",
                )
