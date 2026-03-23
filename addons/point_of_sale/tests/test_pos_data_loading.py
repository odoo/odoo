# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import fields
from odoo.addons.point_of_sale.tests.common import CommonPosTest


@odoo.tests.tagged('post_install', '-at_install')
class TestPosDataLoading(CommonPosTest):
    # Tests for the POS data loading architecture.

    def _get_session(self):
        self.pos_config_usd.open_ui()
        return self.pos_config_usd.current_session_id

    def test_load_data_response_structure(self):
        """load_data() must return fields, relations, dependencies and records for every model."""
        session = self._get_session()
        data = session.load_data()

        self.assertTrue(data, "load_data() should return a non-empty dict")
        for model_name, model_data in data.items():
            self.assertIn('fields', model_data,
                f"[{model_name}] Missing 'fields' key")
            self.assertIn('relations', model_data,
                f"[{model_name}] Missing 'relations' key")
            self.assertIn('records', model_data,
                f"[{model_name}] Missing 'records' key")
            self.assertIsInstance(model_data['records'], list,
                f"[{model_name}] 'records' should be a list")

    def test_load_data_pos_session_and_config_present(self):
        """pos.session and pos.config must always be present in the response."""
        session = self._get_session()
        data = session.load_data()

        self.assertIn('pos.session', data)
        self.assertIn('pos.config', data)
        self.assertTrue(data['pos.session']['records'],
            "pos.session should have at least one record")
        self.assertTrue(data['pos.config']['records'],
            "pos.config should have at least one record")

    def test_load_data_relations_contain_relational_fields(self):
        """Relations metadata must include many2one/one2many/many2many field entries."""
        session = self._get_session()
        data = session.load_data()

        product_relations = data['product.product']['relations']
        relational_types = {v['type'] for v in product_relations.values()}
        self.assertTrue(
            relational_types & {'many2one', 'one2many', 'many2many'},
            "product.product relations should contain relational field types"
        )

    def test_load_data_relations_many2one_has_ondelete(self):
        """Many2one relation entries should carry the ondelete attribute when set."""
        session = self._get_session()
        data = session.load_data()

        # product.template.categ_id is many2one with ondelete defined
        product_relations = data['product.template']['relations']
        categ_rel = product_relations.get('categ_id')
        self.assertIsNotNone(categ_rel, "product.template should have 'categ_id' in relations")
        self.assertEqual(categ_rel['type'], 'many2one')
        self.assertIn('ondelete', categ_rel,
            "many2one relation with ondelete should expose 'ondelete' key")

    # -------------------------------------------------------------------------
    # only_records mode
    # -------------------------------------------------------------------------

    def test_load_data_only_records_flat_structure(self):
        """only_records=True must return a flat {model: [list]} dict without metadata."""
        session = self._get_session()
        data = session.load_data({'only_records': True})

        self.assertTrue(data)
        for model_name, records in data.items():
            self.assertIsInstance(records, list)

    def test_load_data_only_records_contains_session(self):
        """only_records=True must still include pos.session and pos.config records."""
        session = self._get_session()
        data = session.load_data({'only_records': True})

        self.assertIn('pos.session', data)
        self.assertIn('pos.config', data)
        self.assertTrue(data['pos.session'])
        self.assertTrue(data['pos.config'])

    # -------------------------------------------------------------------------
    # write_date always present
    # -------------------------------------------------------------------------

    def test_load_data_write_date_always_present(self):
        """write_date must be included in every loaded record for every model (except ir.ui.view)."""
        session = self._get_session()
        data = session.load_data({'only_records': True})

        for model_name, records in data.items():
            if model_name == 'ir.ui.view':
                continue
            for record in records:
                self.assertIn('write_date', record,
                    f"[{model_name}] record id={record.get('id')} is missing 'write_date'")

    # -------------------------------------------------------------------------
    # Selective model loading via 'models'
    # -------------------------------------------------------------------------

    def test_load_data_models_filter_limits_records(self):
        """Passing 'models' should return records only for the requested models;
        other models are present with empty records."""
        session = self._get_session()
        data = session.load_data({'models': ['product.product']})

        # Requested model should have records
        self.assertIn('product.product', data)
        # Every model in the response must have metadata keys
        for model_name, model_data in data.items():
            if model_name != 'product.product':
                self.assertEqual(model_data['records'], [],
                    f"[{model_name}] Should have empty records when not in requested models")

    # -------------------------------------------------------------------------
    # Incremental sync — skipping up-to-date records
    # -------------------------------------------------------------------------

    def test_load_data_incremental_skips_up_to_date_records(self):
        """Records whose local timestamp is in the future should not be returned."""
        session = self._get_session()
        full_data = session.load_data({'only_records': True})
        config_records = full_data['pos.config']
        self.assertTrue(config_records)

        config_id = config_records[0]['id']
        config_ts = fields.Datetime.from_string(config_records[0]['write_date']).timestamp()

        result = session.load_data({
            'models': ['pos.config'],
            'records': {'pos.config': {str(config_id): config_ts}},
            'only_records': True,
        })
        self.assertEqual(result.get('pos.config', []), [],
            "Up-to-date record should be skipped in incremental load")

    def test_load_data_incremental_returns_outdated_records(self):
        """Records with a local timestamp of 0 (never synced) must always be returned."""
        session = self._get_session()
        full_data = session.load_data({'only_records': True})
        config_id = full_data['pos.config'][0]['id']

        result = session.load_data({
            'models': ['pos.config'],
            'records': {'pos.config': {str(config_id): 0}},
            'only_records': True,
        })
        self.assertTrue(result.get('pos.config'),
            "Outdated record (ts=0) should be returned in incremental load")

    # -------------------------------------------------------------------------
    # to_remove mechanic
    # -------------------------------------------------------------------------

    def test_load_data_to_remove_deleted_record(self):
        """Deleted record IDs should appear in to_remove for that model."""
        session = self._get_session()

        category = self.env['pos.category'].create({'name': 'Temp Category'})
        deleted_id = category.id
        category.unlink()

        data = session.load_data({
            'records': {'pos.category': {str(deleted_id): 0}},
        })
        to_remove = data.get('pos.category', {}).get('to_remove', [])
        self.assertIn(deleted_id, to_remove,
            "Deleted record ID should be listed in to_remove")

    def test_load_data_to_remove_deactivated_record(self):
        """Deactivated (active=False) record IDs should also appear in to_remove."""
        session = self._get_session()

        product = self.env['product.template'].create([{
            'name': 'Active product',
            'list_price': 100.0,
        }])
        deactivated_id = product.id
        product.active = False

        data = session.load_data({
            'records': {'product.template': {str(deactivated_id): 0}},
        })
        to_remove = data.get('product.template', {}).get('to_remove', [])
        self.assertIn(deactivated_id, to_remove,
            "Deactivated record ID should be listed in to_remove")

    def test_load_data_active_record_not_in_to_remove(self):
        """Active, existing records must NOT appear in to_remove."""
        session = self._get_session()
        full_data = session.load_data({'only_records': True})
        config_id = full_data['pos.config'][0]['id']

        data = session.load_data({
            'records': {'pos.config': {str(config_id): 0}},
        })
        to_remove = data.get('pos.config', {}).get('to_remove', [])
        self.assertNotIn(config_id, to_remove,
            "Active record should not appear in to_remove")

    # -------------------------------------------------------------------------
    # filter_local_data
    # -------------------------------------------------------------------------

    def test_filter_local_data_returns_nonexistent_ids(self):
        """filter_local_data should return IDs that don't exist in the DB."""
        session = self._get_session()
        fake_id = 999999999

        result = session.filter_local_data({'pos.category': [str(fake_id)]})
        self.assertIn('pos.category', result)
        self.assertIn(fake_id, result['pos.category'],
            "Non-existent ID should be returned by filter_local_data")

    def test_filter_local_data_does_not_return_existing_ids(self):
        """filter_local_data should not return IDs that exist and are active."""
        session = self._get_session()
        full_data = session.load_data({'only_records': True})
        config_id = full_data['pos.config'][0]['id']

        result = session.filter_local_data({'pos.config': [str(config_id)]})
        ids_to_remove = result.get('pos.config', [])
        self.assertNotIn(config_id, ids_to_remove,
            "Existing active record should not be returned by filter_local_data")

    # -------------------------------------------------------------------------
    # Pagination via search_params
    # -------------------------------------------------------------------------

    def test_load_data_search_params_limit(self):
        """search_params limit should cap the number of records returned."""
        session = self._get_session()
        data = session.load_data({
            'models': ['product.product'],
            'search_params': {'product.product': {'limit': 1}},
            'only_records': True,
        })
        records = data.get('product.product', [])
        self.assertLessEqual(len(records), 1,
            "search_params limit=1 should return at most 1 product.product record")

    def test_load_data_search_params_offset_returns_different_records(self):
        """offset=0 and offset=1 with limit=1 should return different records."""
        session = self._get_session()

        page1 = session.load_data({
            'models': ['product.product'],
            'search_params': {'product.product': {'limit': 1, 'offset': 0}},
            'only_records': True,
        }).get('product.product', [])

        page2 = session.load_data({
            'models': ['product.product'],
            'search_params': {'product.product': {'limit': 1, 'offset': 1}},
            'only_records': True,
        }).get('product.product', [])

        if page1 and page2:
            self.assertNotEqual(page1[0]['id'], page2[0]['id'],
                "Page 1 and page 2 should return different records")
