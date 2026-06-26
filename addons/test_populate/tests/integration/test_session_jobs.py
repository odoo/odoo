from unittest.mock import patch

from odoo.addons.populate import start_populate
from odoo.addons.populate.models.job import MAX_RECORD_COMMIT_SIZE
from odoo.addons.populate.utils.profiling import (
    get_profile_description,
    get_profile_session_name,
)
from odoo.addons.test_populate.tests.common import PopulateTestCase


class TestSessionFieldGeneration(PopulateTestCase):

    def test_eval_generator(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Eval Generator Test',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'count': 3,
                    'fields': {
                        'name': {'eval': '"Test Product"'},
                        'price': {'eval': '99.99'},
                        'active': {'eval': 'True'},
                        'stock_quantity': {'eval': '100'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        initial_count = self.env['test_populate.product'].search_count([])

        start_populate(session)

        final_count = self.env['test_populate.product'].search_count([])
        self.assertEqual(final_count - initial_count, 3)

        created_products = self.env['test_populate.product'].search([
            ('name', '=', 'Test Product'),
            ('price', '=', 99.99),
            ('active', '=', True),
            ('stock_quantity', '=', 100),
        ])
        self.assertEqual(len(created_products), 3)

    def test_eval_lambda_generator(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Eval Lambda Generator Test',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'count': 5,
                    'fields': {
                        'name': {'eval': '"Product"'},
                        'price': {
                            'generator': 'scalar.float',
                            'start': 10.0,
                            'end': 100.0,
                        },
                        'stock_quantity': {
                            'eval': 'int(price * 2)',
                        },
                        'description': {
                            'eval': 'f"{name} costs ${price:.2f}"',
                        },
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        initial_count = self.env['test_populate.product'].search_count([])

        start_populate(session)

        final_count = self.env['test_populate.product'].search_count([])
        self.assertEqual(final_count - initial_count, 5)

        product_ids = self.env['populate.model.data'].search([
            ('session_id', '=', session.id),
            ('res_model', '=', 'test_populate.product'),
        ]).mapped('res_id')

        created_products = self.env['test_populate.product'].browse(product_ids)
        self.assertEqual(len(created_products), 5)

        for product in created_products:
            expected_stock = int(product.price * 2)
            self.assertEqual(product.stock_quantity, expected_stock)

            expected_description = f"{product.name} costs ${product.price:.2f}"
            self.assertEqual(product.description, expected_description)

            self.assertEqual(product.name, "Product")

    def test_field_with_no_generator_or_eval_uses_field_type_default(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Default Generator Test',
            'definition_json': [{
                'name': 'test_populate.customer',
                'count': 3,
                'fields': {
                    'name': {},         # char
                    'email': {},        # char
                    'age': {},          # integer
                    'is_vip': {},       # boolean
                    'total_spent': {},  # float
                },
            }],
        })
        session = self.env['populate.session'].create({'blueprint_id': blueprint.id})
        start_populate(session)

        customer_ids = self.env['populate.model.data'].search([
            ('session_id', '=', session.id),
        ]).mapped('res_id')
        customers = self.env['test_populate.customer'].browse(customer_ids)
        self.assertEqual(len(customers), 3)

        for customer in customers:
            self.assertTrue(customer.name)
            self.assertTrue(customer.email)

    def test_field_with_no_generator_unknown_type_raises(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Unknown Type Test',
            'definition_json': [{
                'name': 'test_populate.product',
                'count': 1,
                'fields': {
                    'name': {'generator': 'textual.char'},
                    'v_thing': {'virtual': True},  # virtual fields don't have a default generator
                },
            }],
        })
        session = self.env['populate.session'].create({'blueprint_id': blueprint.id})
        with self.assertRaises(ValueError) as cm:
            start_populate(session)

        self.assertIn('v_thing', str(cm.exception))

    def test_explicit_eval_is_not_overridden_by_default(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Eval Priority Test',
            'definition_json': [{
                'name': 'test_populate.product',
                'count': 3,
                'fields': {
                    'name': {'eval': '"Fixed"'},
                    'is_sellable': {'eval': 'True'},
                },
            }],
        })
        session = self.env['populate.session'].create({'blueprint_id': blueprint.id})
        start_populate(session)

        product_ids = self.env['populate.model.data'].search([
            ('session_id', '=', session.id),
        ]).mapped('res_id')
        products = self.env['test_populate.product'].browse(product_ids)
        self.assertTrue(all(p.name == 'Fixed' for p in products))


class TestWriteJobTargeting(PopulateTestCase):

    def test_write_without_ref_generates_values_for_existing_records(self):
        existing_products = self.env['test_populate.product'].create([
            {'name': 'Product 1', 'price': 10.0},
            {'name': 'Product 2', 'price': 20.0},
        ])

        blueprint = self.env['populate.blueprint'].create({
            'name': 'Write Test Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'type': 'write',
                    'count': 1,
                    'fields': {
                        'description': {'generator': 'textual.text', 'length': 50, 'null_ratio': 0},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        start_populate(session)

        updated_products = self.env['test_populate.product'].browse(existing_products.ids)
        for product in updated_products:
            self.assertTrue(product.description)

    def test_write_with_plain_ref_updates_created_records(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Create and Write Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.supplier',
                    'ref': 'test_suppliers',
                    'count': 2,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 20},
                        'email': {'generator': 'textual.char', 'length': 25},
                        'is_active': {'eval': 'True', 'null_ratio': 0},
                    },
                },
                {
                    'name': 'test_populate.supplier',
                    'type': 'write',
                    'ref': 'test_suppliers',
                    'fields': {
                        'rating': {'generator': 'scalar.float', 'start': 4.0, 'end': 5.0, 'null_ratio': 0},
                        'notes': {'eval': '"Updated via write job"', 'null_ratio': 0},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        initial_supplier_count = self.env['test_populate.supplier'].search_count([])

        start_populate(session)

        final_supplier_count = self.env['test_populate.supplier'].search_count([])

        self.assertEqual(final_supplier_count - initial_supplier_count, 2)

        model_data_entries = self.env['populate.model.data'].search([
            ('res_model', '=', 'test_populate.supplier'),
            ('session_id', '=', session.id),
            ('ref', '=', 'test_suppliers'),
        ])
        self.assertEqual(len(model_data_entries), 2)

        created_supplier_ids = [entry.res_id for entry in model_data_entries]
        updated_suppliers = self.env['test_populate.supplier'].browse(created_supplier_ids)

        for supplier in updated_suppliers:
            self.assertTrue(supplier.is_active)
            self.assertTrue(supplier.rating)
            self.assertEqual(supplier.notes, "Updated via write job")

    def test_write_job_without_ref_updates_all_records(self):
        existing_suppliers = self.env['test_populate.supplier'].create([
            {'name': 'Existing Supplier 1', 'is_active': True},
            {'name': 'Existing Supplier 2', 'is_active': True},
        ])

        blueprint = self.env['populate.blueprint'].create({
            'name': 'Write All Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.supplier',
                    'type': 'write',
                    'fields': {
                        'notes': {'eval': '"Global update"', 'null_ratio': 0},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        start_populate(session)

        updated_suppliers = self.env['test_populate.supplier'].browse(existing_suppliers.ids)
        for supplier in updated_suppliers:
            self.assertEqual(supplier.notes, "Global update")

    def test_write_job_with_domain_only_updates_matching_records(self):
        us_supplier, ca_supplier = self.env['test_populate.supplier'].create([{
            'name': 'US Supplier',
            'country_code': 'US',
        }, {
            'name': 'CA Supplier',
            'country_code': 'CA',
        }])

        blueprint = self.env['populate.blueprint'].create({
            'name': 'Write Domain Blueprint',
            'definition_json': [{
                'name': 'test_populate.supplier',
                'type': 'write',
                'domain': "[('country_code', '=', 'US')]",
                'fields': {
                    'notes': {'eval': '"Domain update"'},
                },
            }],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        start_populate(session)

        self.assertEqual(us_supplier.notes, "Domain update")
        self.assertFalse(ca_supplier.notes)

    def test_write_job_with_ref_and_domain_updates_intersection(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Write Ref Domain Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.supplier',
                    'ref': 'mixed_suppliers',
                    'count': 2,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 20},
                        'v_index': {
                            'virtual': True,
                            'generator': 'misc.counter',
                            'start': 0,
                            'end': 2,
                        },
                        'country_code': {'eval': '"US" if v_index == 0 else "CA"'},
                    },
                },
                {
                    'name': 'test_populate.supplier',
                    'type': 'write',
                    'ref': 'mixed_suppliers',
                    'domain': "[('country_code', '=', 'US')]",
                    'fields': {
                        'notes': {'eval': '"Intersection update"'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })
        write_job = session.job_ids.filtered(lambda job: job.type == 'write')
        self.assertEqual(write_job.domain, "[('country_code', '=', 'US')]")
        self.assertEqual(
            write_job.record_count,
            2,
            "The domain cannot narrow records that do not exist yet, so a plain ref write keeps "
            "the referenced create count as an upper bound.",
        )

        start_populate(session)

        supplier_ids = self.env['populate.model.data'].search([
            ('session_id', '=', session.id),
            ('res_model', '=', 'test_populate.supplier'),
            ('ref', '=', 'mixed_suppliers'),
        ]).mapped('res_id')
        suppliers = self.env['test_populate.supplier'].browse(supplier_ids)

        us_supplier = suppliers.filtered(lambda supplier: supplier.country_code == 'US')
        ca_supplier = suppliers.filtered(lambda supplier: supplier.country_code == 'CA')
        self.assertEqual(us_supplier.notes, "Intersection update")
        self.assertFalse(ca_supplier.notes)


class TestWriteJobRecordCount(PopulateTestCase):

    def test_write_job_record_count_with_ref(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Write Ref Count Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.customer',
                    'count': 50,
                    'ref': 'my_customers',
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 10},
                        'email': {'generator': 'textual.char', 'length': 15},
                    },
                },
                {
                    'name': 'test_populate.customer',
                    'type': 'write',
                    'ref': 'my_customers',
                    'fields': {
                        'is_vip': {'eval': 'True'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        jobs = session.job_ids
        create_job = jobs.filtered(lambda j: j.type == 'create')
        write_job = jobs.filtered(lambda j: j.type == 'write')

        self.assertEqual(create_job.record_count, 50)
        self.assertEqual(write_job.record_count, 50,
                         "Write job should have the same record_count as the referenced create job")

    def test_write_job_record_count_without_ref_existing_records(self):
        self.env['test_populate.customer'].create([
            {'name': f'Customer {i}', 'email': f'c{i}@test.com'}
            for i in range(10)
        ])

        blueprint = self.env['populate.blueprint'].create({
            'name': 'Write No Ref Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.customer',
                    'type': 'write',
                    'fields': {
                        'is_vip': {'eval': 'True'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        write_job = session.job_ids.filtered(lambda j: j.type == 'write')
        expected_count = self.env['test_populate.customer'].search_count([])
        self.assertEqual(write_job.record_count, expected_count,
                         "Write job without ref should have record_count equal to existing records in DB")

    def test_write_job_record_count_without_ref_counts_domain_matches_plus_preceding_creates(self):
        self.env['test_populate.customer'].create([
            {'name': 'Young Customer', 'email': 'young@test.com', 'age': 10},
            {'name': 'Adult Customer', 'email': 'adult@test.com', 'age': 25},
            {'name': 'Senior Customer', 'email': 'senior@test.com', 'age': 60},
        ])

        blueprint = self.env['populate.blueprint'].create({
            'name': 'Create Then Write Domain No Ref Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.customer',
                    'count': 5,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 10},
                        'email': {'generator': 'textual.char', 'length': 15},
                    },
                },
                {
                    'name': 'test_populate.customer',
                    'type': 'write',
                    'domain': "[('age', '>=', 20)]",
                    'fields': {
                        'is_vip': {'eval': 'True'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        write_job = session.job_ids.filtered(lambda job: job.type == 'write')
        self.assertEqual(
            write_job.record_count,
            7,
            "No-ref write count should be matching existing records plus all preceding creates for the model.",
        )

    def test_write_job_record_count_without_ref_includes_preceding_creates(self):
        existing = self.env['test_populate.customer'].create([
            {'name': 'Existing', 'email': 'existing@test.com'},
        ])

        blueprint = self.env['populate.blueprint'].create({
            'name': 'Create Then Write No Ref Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.customer',
                    'count': 20,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 10},
                        'email': {'generator': 'textual.char', 'length': 15},
                    },
                },
                {
                    'name': 'test_populate.customer',
                    'count': 10,
                    'ref': 'referenced_customers',
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 10},
                        'email': {'generator': 'textual.char', 'length': 15},
                    },
                },
                {
                    'name': 'test_populate.customer',
                    'type': 'write',
                    'fields': {
                        'is_vip': {'eval': 'True'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        write_job = session.job_ids.filtered(lambda j: j.type == 'write')
        self.assertEqual(
            write_job.record_count,
            len(existing) + 30,
            "Write job without ref should count existing records "
            "+ all preceding create jobs (with refs or not) for the model",
        )

    def test_write_job_scaling_factor_applied_to_record_count(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Scaled Write Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.customer',
                    'count': 100,
                    'ref': 'scaled_customers',
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 10},
                        'email': {'generator': 'textual.char', 'length': 15},
                    },
                },
                {
                    'name': 'test_populate.customer',
                    'type': 'write',
                    'ref': 'scaled_customers',
                    'fields': {
                        'is_vip': {'eval': 'True'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
            'scaling_factor': 5.0,
        })

        create_job = session.job_ids.filtered(lambda j: j.type == 'create' and not j.parent_id)
        write_job = session.job_ids.filtered(lambda j: j.type == 'write' and not j.parent_id)

        self.assertEqual(create_job.record_count, 500)  # 100 * 5.0
        self.assertEqual(write_job.record_count, 500,
                         "Write job record_count should match the scaled create count")

    def test_multiple_create_jobs_same_model_no_ref_write(self):
        self.env['test_populate.customer'].create([
            {'name': 'Pre-existing', 'email': 'pre@test.com'},
        ])
        existing_count = self.env['test_populate.customer'].search_count([])

        blueprint = self.env['populate.blueprint'].create({
            'name': 'Multi Create Then Write Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.customer',
                    'count': 10,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 10},
                        'email': {'generator': 'textual.char', 'length': 15},
                    },
                },
                {
                    'name': 'test_populate.customer',
                    'count': 15,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 10},
                        'email': {'generator': 'textual.char', 'length': 15},
                    },
                },
                {
                    'name': 'test_populate.customer',
                    'type': 'write',
                    'fields': {
                        'notes': {'eval': '"batch update"', 'null_ratio': 0},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        write_job = session.job_ids.filtered(lambda j: j.type == 'write')
        expected = existing_count + 10 + 15
        self.assertEqual(write_job.record_count, expected,
                         "Write job without ref should sum existing records + all preceding unreferenced creates")


class TestProfilerIntegration(PopulateTestCase):

    def setUp(self):
        super().setUp()
        # Profiler saves rows through its own db_connect(). Route that cursor
        # through the test registry so rows stay inside TestCursor savepoints.
        self.startPatcher(patch('odoo.sql_db.db_connect', return_value=self.registry))

    def _profiles_for_session(self, session):
        return self.env['ir.profile'].search([
            ('session', '=like', f'%{get_profile_session_name(session)}'),
        ], order='name')

    def test_populate_without_profile_does_not_create_profile_rows(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Unprofiled Populate Test',
            'definition_json': [{
                'name': 'test_populate.product',
                'count': 1,
                'fields': {
                    'name': {'eval': '"Unprofiled"'},
                },
            }],
        })
        session = self.env['populate.session'].create({'blueprint_id': blueprint.id})

        start_populate(session)

        self.assertFalse(self._profiles_for_session(session))

    def test_populate_with_profile_creates_profile_per_executable_job(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Profiled Populate Test',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'ref': 'profiled_products',
                    'count': 2,
                    'fields': {
                        'name': {'eval': '"Profiled"'},
                    },
                },
                {
                    'name': 'test_populate.product',
                    'type': 'write',
                    'ref': 'profiled_products',
                    'fields': {
                        'description': {'eval': '"Updated by profiled write"'},
                    },
                },
            ],
        })
        session = self.env['populate.session'].create({'blueprint_id': blueprint.id})

        start_populate(session, profile=True)

        profiles = self._profiles_for_session(session)
        self.assertEqual(len(profiles), len(session.job_ids))
        self.assertCountEqual(
            profiles.mapped('name'),
            [get_profile_description(job) for job in session.job_ids],
        )

        profile_sessions = set(profiles.mapped('session'))
        self.assertEqual(len(profile_sessions), 1)
        self.assertTrue(
            profile_sessions.pop().endswith(
                get_profile_session_name(session),
            ),
        )

    def test_populate_with_profile_ignores_planner_jobs_and_profiles_subjobs(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Profiled Split Populate Test',
            'definition_json': [{
                'name': 'test_populate.product',
                'count': MAX_RECORD_COMMIT_SIZE + 1,
                'fields': {
                    'name': {'eval': '"Profiled Split"'},
                },
            }],
        })
        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
            'worker_count': 1,
        })
        job = session.job_ids.ensure_one()
        # Split parent jobs only coordinate subjobs; they must not get their own profile row.
        self.assertFalse(job.is_executable)

        start_populate(session, profile=True)

        profiles = self._profiles_for_session(session)
        self.assertEqual(len(profiles), len(job.child_ids))
        self.assertCountEqual(
            profiles.mapped('name'),
            [get_profile_description(subjob) for subjob in job.child_ids],
        )
        self.assertNotIn(get_profile_description(job), profiles.mapped('name'))


class TestSubjobs(PopulateTestCase):

    def test_large_create_job_is_split_into_subjobs(self):
        create_count = 25000
        self.assertGreater(create_count, MAX_RECORD_COMMIT_SIZE)

        blueprint = self.env['populate.blueprint'].create({
            'name': 'Large Count Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'count': create_count,
                    'fields': {
                        'name': {'generator': 'textual.char'},
                        'price': {'generator': 'scalar.float'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        self.assertTrue(session.job_ids.child_ids)

    def test_large_write_job_with_plain_ref_is_split_into_subjobs(self):
        create_count = 25000
        self.assertGreater(create_count, MAX_RECORD_COMMIT_SIZE)

        blueprint = self.env['populate.blueprint'].create({
            'name': 'Large Write Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.customer',
                    'count': create_count,
                    'ref': 'big_customers',
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 10},
                        'email': {'generator': 'textual.char', 'length': 15},
                    },
                },
                {
                    'name': 'test_populate.customer',
                    'type': 'write',
                    'ref': 'big_customers',
                    'fields': {
                        'is_vip': {'eval': 'True'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        write_job = session.job_ids.filtered(lambda j: j.type == 'write' and not j.parent_id)
        self.assertTrue(write_job.child_ids,
                        "Write job with large record_count should be split into subjobs")
        self.assertEqual(write_job.record_count, create_count)
        self.assertEqual(
            sum(write_job.child_ids.mapped('record_count')),
            write_job.record_count,
            "Subjobs record counts should sum up to parent's record_count",
        )

    def test_write_subjobs_apply_offset_and_limit_after_domain(self):
        create_count = 1205
        self.assertGreater(create_count, MAX_RECORD_COMMIT_SIZE)

        non_matching_customers = self.env['test_populate.customer'].create([
            {'name': f'Young Customer {i}', 'email': f'young{i}@test.com', 'age': 10}
            for i in range(5)
        ])
        matching_customers = self.env['test_populate.customer'].create([
            {'name': f'Adult Customer {i}', 'email': f'adult{i}@test.com', 'age': 20}
            for i in range(create_count)
        ])

        blueprint = self.env['populate.blueprint'].create({
            'name': 'Split Write Domain Blueprint',
            'definition_json': [{
                'name': 'test_populate.customer',
                'type': 'write',
                'domain': "[('age', '>=', 20)]",
                'fields': {
                    'notes': {'eval': '"Domain split update"'},
                },
            }],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        write_job = session.job_ids.filtered(lambda j: j.type == 'write' and not j.parent_id)
        self.assertEqual(write_job.record_count, len(matching_customers))
        self.assertTrue(write_job.child_ids, "The domain-targeted write job should be split into subjobs")
        self.assertEqual(sum(write_job.child_ids.mapped('record_count')), len(matching_customers))

        start_populate(session)

        self.assertTrue(all(customer.notes == "Domain split update" for customer in matching_customers))
        self.assertFalse(any(customer.notes for customer in non_matching_customers))


class TestDottedRefTargeting(PopulateTestCase):
    """Tests for the get_ref_domain() dotted-path (ref.field) feature."""

    def test_write_job_with_relational_ref_targets_corecords(self):
        """
        A write job with ref='some_ref.relation_field' should update
        records reachable via the relational path, not the ref'd records themselves.
        """
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Relational Ref Write Test',
            'definition_json': [
                {
                    'name': 'test_populate.supplier',
                    'ref': 'test_suppliers',
                    'count': 2,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 20},
                        'is_active': {'eval': 'True'},
                    },
                },
                {
                    'name': 'test_populate.product',
                    'count': 4,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 15},
                        'price': {'generator': 'scalar.float', 'start': 10.0, 'end': 100.0},
                        'supplier_id': {
                            'generator': 'relation.one',
                            'ref': 'test_suppliers',
                            'null_ratio': '0.0',
                        },
                    },
                },
                {
                    # Write on products reachable via supplier_ids.product_ids
                    'name': 'test_populate.product',
                    'type': 'write',
                    'ref': 'test_suppliers.product_ids',
                    'fields': {
                        'description': {'eval': '"Updated via relational ref"', 'null_ratio': '0'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({'blueprint_id': blueprint.id})

        start_populate(session)

        supplier_model_data = self.env['populate.model.data'].search([
            ('session_id', '=', session.id),
            ('res_model', '=', 'test_populate.supplier'),
        ])
        created_supplier_ids = supplier_model_data.mapped('res_id')
        suppliers = self.env['test_populate.supplier'].browse(created_supplier_ids)

        # Products linked to our suppliers should have been updated
        linked_products = suppliers.mapped('product_ids')
        self.assertTrue(linked_products, "Expected products linked to populated suppliers")
        for product in linked_products:
            self.assertEqual(product.description, "Updated via relational ref")

    def test_write_job_with_multilevel_relational_ref(self):
        """
        Exercises a multi-level relational path across three distinct models:
          'test_warehouses_ml.supplier_ids.product_ids'

        Chain:
          test_populate.warehouse  (ref'd)
            -> .supplier_ids       (one2many -> test_populate.supplier)
            -> .product_ids        (one2many -> test_populate.product)

        The write job targets test_populate.product records reachable via
        the two-hop traversal. Products not linked to any of the ref'd
        warehouses' suppliers must NOT be updated.
        """
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Multilevel Relational Ref Write Test',
            'definition_json': [
                {
                    'name': 'test_populate.warehouse',
                    'ref': 'test_warehouses_ml',
                    'count': 2,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 15},
                    },
                },
                {
                    'name': 'test_populate.supplier',
                    'count': 3,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 20},
                        'warehouse_id': {
                            'generator': 'relation.one',
                            'ref': 'test_warehouses_ml',
                            'null_ratio': '0.0',
                        },
                    },
                },
                {
                    'name': 'test_populate.product',
                    'count': 6,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 15},
                        'price': {'generator': 'scalar.float', 'start': 1.0, 'end': 100.0},
                        'supplier_id': {
                            'generator': 'relation.one',
                            'null_ratio': '0.0',
                        },
                    },
                },
                {
                    # Two-level path: warehouse -> supplier_ids -> product_ids
                    # Only products whose supplier belongs to one of the ref'd warehouses
                    # should be updated.
                    'name': 'test_populate.product',
                    'type': 'write',
                    'ref': 'test_warehouses_ml.supplier_ids.product_ids',
                    'fields': {
                        'description': {'eval': '"Updated via multi-level ref"', 'null_ratio': '0'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({'blueprint_id': blueprint.id})

        start_populate(session)

        warehouse_ids = self.env['populate.model.data'].search([
            ('session_id', '=', session.id),
            ('res_model', '=', 'test_populate.warehouse'),
        ]).mapped('res_id')
        warehouses = self.env['test_populate.warehouse'].browse(warehouse_ids)

        reachable_products = warehouses.mapped('supplier_ids.product_ids')
        self.assertTrue(reachable_products, "Expected products reachable via the multi-level path")

        for product in reachable_products:
            self.assertEqual(
                product.description,
                "Updated via multi-level ref",
                f"Product {product.name!r} reachable via warehouse->supplier->product should be updated",
            )

        # Products whose supplier is NOT under any ref'd warehouse must be untouched.
        all_product_ids = self.env['populate.model.data'].search([
            ('session_id', '=', session.id),
            ('res_model', '=', 'test_populate.product'),
        ]).mapped('res_id')
        all_products = self.env['test_populate.product'].browse(all_product_ids)
        unreachable_products = all_products - reachable_products

        for product in unreachable_products:
            self.assertNotEqual(
                product.description,
                "Updated via multi-level ref",
                f"Product {product.name!r} outside the ref chain should NOT be updated",
            )

    def test_write_job_relational_ref_record_count_is_zero_at_creation(self):
        """
        A write job with a dotted ref (ref.relation) cannot know its record_count
        at creation time — it should be stored as 0 (None semantics).
        """
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Relational Ref Zero Count Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.supplier',
                    'ref': 'ref_suppliers',
                    'count': 3,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 20},
                        'is_active': {'eval': 'True'},
                    },
                },
                {
                    'name': 'test_populate.product',
                    'type': 'write',
                    'ref': 'ref_suppliers.product_ids',
                    'fields': {
                        'description': {'eval': '"rel ref write"', 'null_ratio': '0'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({'blueprint_id': blueprint.id})

        write_job = session.job_ids.filtered(
            lambda j: j.type == 'write' and not j.parent_id,
        )
        self.assertEqual(len(write_job), 1)
        self.assertEqual(
            write_job.record_count, 0,
            "Write job with relational ref should have record_count=0 (unknown at creation time)",
        )

    def test_write_job_relational_ref_not_split_into_subjobs(self):
        """
        A write job with record_count=0 (relational ref) must NOT be split into subjobs,
        since the cardinality is unknown.
        """
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Relational Ref No Split Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.supplier',
                    'ref': 'suppliers_nosplit',
                    'count': 30000,  # Large enough that a known count would trigger a split
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 20},
                        'is_active': {'eval': 'True'},
                    },
                },
                {
                    'name': 'test_populate.product',
                    'type': 'write',
                    'ref': 'suppliers_nosplit.product_ids',
                    'fields': {
                        'description': {'eval': '"no split"', 'null_ratio': '0'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
            'worker_count': 3,
        })

        write_job = session.job_ids.filtered(
            lambda j: j.type == 'write' and not j.parent_id,
        )
        self.assertFalse(
            write_job.child_ids,
            "Write job with unknown record_count (relational ref) should not be split into subjobs",
        )

    def test_write_job_relational_ref_with_domain_keeps_unknown_count_and_no_subjobs(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Relational Ref Domain No Split Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.supplier',
                    'ref': 'suppliers_domain_nosplit',
                    'count': 30000,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 20},
                    },
                },
                {
                    'name': 'test_populate.product',
                    'type': 'write',
                    'ref': 'suppliers_domain_nosplit.product_ids',
                    'domain': "[('category', '=', 'books')]",
                    'fields': {
                        'description': {'eval': '"domain no split"', 'null_ratio': '0'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
            'worker_count': 3,
        })

        write_job = session.job_ids.filtered(
            lambda job: job.type == 'write' and not job.parent_id,
        )
        self.assertEqual(write_job.record_count, 0)
        self.assertEqual(write_job.domain, "[('category', '=', 'books')]")
        self.assertFalse(
            write_job.child_ids,
            "Dotted-ref writes stay unsplit even when they also have a domain.",
        )
