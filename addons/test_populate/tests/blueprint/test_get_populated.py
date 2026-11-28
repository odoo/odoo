from odoo.addons.populate import start_populate
from odoo.addons.test_populate.tests.common import PopulateTestCase


class TestGetPopulated(PopulateTestCase):
    def setUp(self):
        super().setUp()
        self.blueprint = self.env['populate.blueprint'].create({
            'name': 'Products',
            'definition_xml': '''
                <create model="test_populate.product" id="products" count="3">
                    <field name="name" eval="'Product'"/>
                </create>
            ''',
        })

    def _populate(self, blueprint, **values):
        session = self.env['populate.session'].create({'blueprint_id': blueprint.id, 'seed': 42, **values})
        start_populate(session)
        return session

    def test_unknown_reference_is_an_error_even_without_sessions(self):
        with self.assertRaisesRegex(ValueError, 'Unknown create reference'):
            self.blueprint._get_populated('unknown')

    def test_combines_completed_sessions(self):
        self._populate(self.blueprint)
        self._populate(self.blueprint, scaling_factor=2)
        self.assertEqual(len(self.blueprint._get_populated('products')), 9)

    def test_excludes_records_until_the_whole_session_is_finished(self):
        self.blueprint.definition_xml = '''
            <create model="test_populate.product" id="products" count="3">
                <field name="name" eval="'Product'"/>
            </create>
            <write model="test_populate.product" ref="products">
                <field name="price" eval="1.0"/>
            </write>
        '''
        unfinished = self.env['populate.session'].create({'blueprint_id': self.blueprint.id})
        # The create job is done, but the preparation write is still pending.
        unfinished.job_ids.filtered(lambda job: job.operation == 'create')._execute()
        self._populate(self.blueprint)
        self.assertEqual(len(self.blueprint._get_populated('products')), 3)

    def test_orders_records_by_id(self):
        session = self._populate(self.blueprint)
        entries = self.env['populate.model.data'].search([('session_id', '=', session.id)], order='res_id')
        expected_ids = entries.mapped('res_id')
        entries.unlink()
        self.env['populate.model.data'].create([
            {'job_id': session.job_ids.id, 'res_id': record_id}
            for record_id in reversed(expected_ids)
        ])
        self.assertEqual(self.blueprint._get_populated('products').ids, expected_ids)

    def test_valid_reference_without_entries_returns_an_empty_recordset(self):
        session = self._populate(self.blueprint)
        self.env['populate.model.data'].search([('session_id', '=', session.id)]).unlink()
        self.assertEqual(self.blueprint._get_populated('products'), self.env['test_populate.product'])

    def test_imported_references_remain_distinct(self):
        self.env['ir.model.data'].create({
            'module': 'test_populate', 'name': 'imported_products',
            'model': self.blueprint._name, 'res_id': self.blueprint.id,
        })
        caller = self.env['populate.blueprint'].create({
            'name': 'Composed products',
            'definition_xml': '''
                <import ref="test_populate.imported_products" as="sale"/>
                <import ref="test_populate.imported_products" as="purchase"/>
            ''',
        })
        self._populate(caller)
        sale = caller._get_populated('sale/products')
        purchase = caller._get_populated('purchase/products')
        self.assertEqual((len(sale), len(purchase)), (3, 3))
        self.assertFalse(sale & purchase)

    def test_split_create_job_returns_all_records(self):
        self.blueprint.definition_xml = self.blueprint.definition_xml.replace('count="3"', 'count="1001"')
        session = self._populate(self.blueprint)
        self.assertGreater(len(session.job_ids.child_ids), 1)
        self.assertEqual(len(self.blueprint._get_populated('products')), 1001)
