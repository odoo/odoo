# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged('post_install', '-at_install')
class TestSelfOrderDataLoading(SelfOrderCommonTest):
    # Tests for the self-order data loading architecture.

    def _open_self_order_config(self, mode='kiosk'):
        self.pos_config.write({'self_ordering_mode': mode})
        self.pos_config.open_ui()
        session = self.pos_config.current_session_id
        session.set_opening_control(0, "")
        return self.pos_config

    def test_load_self_data_response_structure(self):
        """load_self_data() must return fields, relations and records for every model."""
        config = self._open_self_order_config()
        data = config.load_self_data()

        self.assertTrue(data, "load_self_data() should return a non-empty dict")
        for model_name, model_data in data.items():
            self.assertIn('fields', model_data,
                f"[{model_name}] Missing 'fields' key")
            self.assertIn('relations', model_data,
                f"[{model_name}] Missing 'relations' key")
            self.assertIn('records', model_data,
                f"[{model_name}] Missing 'records' key")
            self.assertIsInstance(model_data['records'], list,
                f"[{model_name}] 'records' should be a list")

    def test_load_self_data_pos_config_present(self):
        """pos.config must be present in the response with the loaded config record."""
        config = self._open_self_order_config()
        data = config.load_self_data()

        self.assertIn('pos.config', data)
        config_ids = [r['id'] for r in data['pos.config']['records']]
        self.assertIn(config.id, config_ids,
            "The pos.config record should be present in load_self_data()")

    def test_load_self_data_contains_expected_models(self):
        """All models declared in _load_self_data_models() must be present in the response."""
        config = self._open_self_order_config()
        expected_models = config._load_self_data_models()
        data = config.load_self_data()

        for model in expected_models:
            self.assertIn(model, data,
                f"Expected model '{model}' missing from load_self_data() response")

    # -------------------------------------------------------------------------
    # write_date always present
    # -------------------------------------------------------------------------

    def test_load_self_data_write_date_in_records(self):
        """write_date must be present in every record returned by load_self_data()."""
        config = self._open_self_order_config()
        data = config.load_self_data()

        for model_name, model_data in data.items():
            if model_name == 'ir.ui.view':
                continue
            for record in model_data['records']:
                self.assertIn('write_date', record,
                    f"[{model_name}] record id={record.get('id')} is missing 'write_date'")

    # -------------------------------------------------------------------------
    # Self-order-specific models
    # -------------------------------------------------------------------------

    def test_load_self_data_mail_template_loaded(self):
        """mail.template must be present in load_self_data() (added by pos_self_order)."""
        config = self._open_self_order_config()
        data = config.load_self_data()

        self.assertIn('mail.template', data,
            "mail.template should be loaded in self-order data")

    def test_load_self_data_custom_link_loaded(self):
        """pos_self_order.custom_link must be present in load_self_data()."""
        config = self._open_self_order_config()
        data = config.load_self_data()

        self.assertIn('pos_self_order.custom_link', data,
            "pos_self_order.custom_link should be loaded in self-order data")

    def test_load_self_data_ir_ui_view_loaded(self):
        """ir.ui.view must be present in load_self_data()."""
        config = self._open_self_order_config()
        data = config.load_self_data()

        self.assertIn('ir.ui.view', data,
            "ir.ui.view should be loaded in self-order data")

    # -------------------------------------------------------------------------
    # Self-order-specific fields injected into pos.config
    # -------------------------------------------------------------------------

    def test_load_self_data_config_has_self_ordering_fields(self):
        """The pos.config record must expose self-ordering specific fields."""
        config = self._open_self_order_config()
        data = config.load_self_data()

        config_record = data['pos.config']['records'][0]
        self.assertIn('self_ordering_mode', config_record,
            "pos.config record should expose 'self_ordering_mode'")
        self.assertIn('self_ordering_service_mode', config_record,
            "pos.config record should expose 'self_ordering_service_mode'")
        self.assertIn('self_ordering_pay_after', config_record,
            "pos.config record should expose 'self_ordering_pay_after'")

    def test_load_self_data_config_has_image_ids_injected(self):
        """_load_pos_self_data_read must inject _self_ordering_image_home_ids
        and _self_ordering_image_background_ids into the pos.config record."""
        config = self._open_self_order_config()
        data = config.load_self_data()

        config_record = data['pos.config']['records'][0]
        self.assertIn('_self_ordering_image_home_ids', config_record,
            "pos.config record should have '_self_ordering_image_home_ids' injected")
        self.assertIn('_self_ordering_image_background_ids', config_record,
            "pos.config record should have '_self_ordering_image_background_ids' injected")
        self.assertIsInstance(config_record['_self_ordering_image_home_ids'], list,
            "'_self_ordering_image_home_ids' should be a list of IDs")

    def test_load_self_data_config_self_order_pos_flag(self):
        """_load_pos_self_data_read must inject '_self_order_pos': True into pos.config."""
        config = self._open_self_order_config()
        data = config.load_self_data()

        config_record = data['pos.config']['records'][0]
        self.assertIn('_self_order_pos', config_record,
            "pos.config record should have '_self_order_pos' flag")
        self.assertTrue(config_record['_self_order_pos'],
            "'_self_order_pos' should be True")

    # -------------------------------------------------------------------------
    # _load_pos_self_data_domain: scopes pos.session to current config
    # -------------------------------------------------------------------------

    def test_load_self_data_session_scoped_to_config(self):
        """pos.session records should only include sessions for the loaded config."""
        config = self._open_self_order_config()

        other_config = self.env['pos.config'].create({'name': 'Other POS Config'})
        other_config.open_ui()
        other_config.current_session_id.set_opening_control(0, "")

        data = config.load_self_data()
        session_ids = [r['id'] for r in data.get('pos.session', {}).get('records', [])]

        self.assertIn(config.current_session_id.id, session_ids,
            "Current config's session should be in pos.session records")
        self.assertNotIn(other_config.current_session_id.id, session_ids,
            "Other config's session should NOT be in pos.session records of this config")

    # -------------------------------------------------------------------------
    # _self_ordering flag injected into pos.session
    # -------------------------------------------------------------------------

    def test_load_self_data_session_has_self_ordering_flag(self):
        """_load_pos_data_read on pos.session must inject the '_self_ordering' flag."""
        config = self._open_self_order_config(mode='kiosk')
        data = config.current_session_id.load_data()

        session_records = data.get('pos.session', {}).get('records', [])
        self.assertTrue(session_records, "pos.session records should not be empty")
        session_record = session_records[0]
        self.assertIn('_self_ordering', session_record,
            "pos.session record should have '_self_ordering' flag injected")
        self.assertTrue(session_record['_self_ordering'],
            "'_self_ordering' should be True when at least one kiosk/mobile config is active")

    # -------------------------------------------------------------------------
    # relations metadata
    # -------------------------------------------------------------------------

    def test_load_self_data_relations_contain_relational_fields(self):
        """Relations metadata for product.product must contain relational field types."""
        config = self._open_self_order_config()
        data = config.load_self_data()

        product_relations = data['product.product']['relations']
        relational_types = {v['type'] for v in product_relations.values()}
        self.assertTrue(
            relational_types & {'many2one', 'one2many', 'many2many'},
            "product.product relations should contain relational field types"
        )
