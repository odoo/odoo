import shlex
from unittest import SkipTest
from unittest.mock import patch

from odoo.addons.populate import start_populate
from odoo.addons.populate.models.blueprint import PopulateDataMissing
from odoo.addons.test_populate.tests.common import PopulateTestCase


class TestGetPopulated(PopulateTestCase):
    def setUp(self):
        super().setUp()
        self.blueprint = self.env['populate.blueprint'].create({
            'name': 'Benchmark helper fixture',
            'definition_json': [
                {
                    'operation': 'create',
                    'model': 'test_populate.product',
                    'id': 'products',
                    'count': 3,
                    'fields': {'name': {'generator': 'textual.char'}},
                },
                {
                    'operation': 'write',
                    'model': 'test_populate.product',
                    'ref': 'products',
                    'fields': {
                        'price': {'eval': '1.0'},
                        'active': {'eval': 'False'},
                    },
                },
            ],
        })

    def test_reject_call_outside_testing_framework(self):
        with patch('odoo.modules.module.current_test', None), self.assertRaisesRegex(AssertionError, 'testing framework'):
            self.blueprint._get_populated('products')

    def test_validate_reference_before_selecting_session(self):
        for ref in ('unknown', 'products.supplier_id', '', None):
            with self.subTest(ref=ref), self.assertRaisesRegex(ValueError, 'Unknown create reference'):
                self.blueprint._get_populated(ref)

    def test_missing_finished_session_is_skip_with_actionable_command(self):
        self.assertTrue(issubclass(PopulateDataMissing, SkipTest))
        self.blueprint.name = "Benchmark's fixture with spaces & quotes"
        with self.assertRaises(PopulateDataMissing) as error:
            self.blueprint._get_populated('products')
        command = str(error.exception).partition('Run: ')[2]
        self.assertEqual(shlex.split(command), ['odoo-bin', 'populate', '-d', self.cr.dbname, '-b', self.blueprint.name])
        session = self.env['populate.session'].create({'blueprint_id': self.blueprint.id, 'seed': 17})
        with self.assertRaisesRegex(PopulateDataMissing, f'--resume {session.id}'):
            self.blueprint._get_populated('products')
        # Execute the create job, leaving the preparation write pending.
        session.job_ids.filtered(lambda job: job.operation == 'create')._execute()
        with self.assertRaises(PopulateDataMissing):
            self.blueprint._get_populated('products')
        start_populate(session)
        self.assertEqual(len(self.blueprint._get_populated('products')), 3)

    def test_finished_session_ignores_unfinished_sessions_and_orders_records(self):
        unfinished = self.env['populate.session'].create({'blueprint_id': self.blueprint.id, 'seed': 17})
        unfinished.job_ids.filtered(lambda job: job.operation == 'create')._execute()
        finished = self.env['populate.session'].create({
            'blueprint_id': self.blueprint.id,
            'seed': 42,
            'scaling_factor': 1,
            'worker_count': 1,
        })
        start_populate(finished)
        self.assertTrue(finished.is_done)
        self.env['populate.session'].create({'blueprint_id': self.blueprint.id})
        result = self.blueprint._get_populated('products')
        entries = self.env['populate.model.data'].search([('session_id', '=', finished.id)], order='res_id')
        self.assertEqual(result.ids, entries.mapped('res_id'))
        self.assertEqual(result.ids, sorted(result.ids))
        self.assertEqual(len(result), 3)
        self.assertFalse(any(result.mapped('active')))
        self.assertEqual(result.mapped('price'), [1.0] * 3)

    def test_multiple_finished_sessions_fail_with_identifiers(self):
        first = self.env['populate.session'].create({
            'blueprint_id': self.blueprint.id,
            'seed': 17,
            'scaling_factor': 2,
            'worker_count': 1,
        })
        start_populate(first)
        self.assertTrue(first.is_done)
        second = self.env['populate.session'].create({
            'blueprint_id': self.blueprint.id,
            'seed': 29,
            'scaling_factor': 3,
            'worker_count': 1,
        })
        start_populate(second)
        self.assertTrue(second.is_done)
        with self.assertRaises(ValueError) as error:
            self.blueprint._get_populated('products')
        for text in (str(first.id), str(second.id), 'seed=17', 'seed=29', 'scale=2', 'scale=3'):
            self.assertIn(text, str(error.exception))

    def test_deleted_records_fail_instead_of_reducing_dataset(self):
        session = self.env['populate.session'].create({
            'blueprint_id': self.blueprint.id,
            'seed': 42,
            'scaling_factor': 1,
            'worker_count': 1,
        })
        start_populate(session)
        self.assertTrue(session.is_done)
        record = self.blueprint._get_populated('products')[1]
        deleted = record.id
        record.unlink()
        with self.assertRaisesRegex(ValueError, f'Deleted records.*{deleted}'):
            self.blueprint._get_populated('products')

    def test_valid_reference_without_recorded_entries(self):
        session = self.env['populate.session'].create({
            'blueprint_id': self.blueprint.id,
            'seed': 42,
            'scaling_factor': 1,
            'worker_count': 1,
        })
        start_populate(session)
        self.assertTrue(session.is_done)
        self.env['populate.model.data'].search([('session_id', '=', session.id)]).unlink()
        result = self.blueprint._get_populated('products')
        self.assertFalse(result)
        self.assertEqual(result._name, 'test_populate.product')

    def test_imported_reference_uses_resolved_definition(self):
        parent = self.env['populate.blueprint'].create({
            'name': 'Imported products',
            'definition_xml': '''
                <create model="test_populate.product" id="records" count="1">
                    <field name="name" eval="'Imported product'"/>
                </create>
            ''',
        })
        self.env['ir.model.data'].create({
            'module': 'test_populate',
            'name': 'benchmark_helper_import',
            'model': parent._name,
            'res_id': parent.id,
        })
        self.blueprint = self.env['populate.blueprint'].create({
            'name': 'Composed benchmark',
            'definition_xml': '<import ref="test_populate.benchmark_helper_import" as="catalog"/>',
        })
        session = self.env['populate.session'].create({
            'blueprint_id': self.blueprint.id,
            'seed': 42,
            'scaling_factor': 1,
            'worker_count': 1,
        })
        start_populate(session)
        self.assertTrue(session.is_done)
        self.assertEqual(len(self.blueprint._get_populated('catalog/records')), 1)
        with self.assertRaisesRegex(ValueError, 'Unknown create reference'):
            self.blueprint._get_populated('records')

    def test_split_create_job_returns_all_subjob_records(self):
        definition = self.blueprint.definition_json
        definition[0]['count'] = 1001
        self.blueprint.definition_json = definition
        session = self.env['populate.session'].create({
            'blueprint_id': self.blueprint.id,
            'seed': 42,
            'scaling_factor': 1,
            'worker_count': 1,
        })
        start_populate(session)
        self.assertTrue(session.is_done)
        create_job = session.job_ids.filtered(lambda job: job.operation == 'create')
        self.assertGreater(len(create_job.child_ids), 1)
        records = self.blueprint._get_populated('products')
        self.assertEqual(len(records), 1001)
        self.assertEqual(records.ids, sorted(records.ids))
