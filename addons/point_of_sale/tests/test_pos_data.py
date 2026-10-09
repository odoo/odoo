# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.addons.point_of_sale.tests.common import CommonPosTest


@odoo.tests.tagged('post_install', '-at_install')
class TestPosData(CommonPosTest):
    # Tests for the POS data loading architecture.

    def test_session_filter_local_data(self):
        products = (
            self.ten_dollars_no_tax | self.twenty_dollars_no_tax
            | self.ten_dollars_with_5_incl | self.twenty_dollars_with_5_incl
        ).with_context(tracking_disable=True)
        product1, product2, product3, product4 = products
        # Prepare the fixture without notifying other open self-order sessions.
        products._write({'available_in_pos': False})
        config = self.pos_config_usd
        session = self.open_new_session(config=config)

        # Delete one product and archive another one
        products_to_display = [product1.id, product2.id, product3.id]
        product1.write({'active': False})
        product2.unlink()
        models_to_filter = {'product.template': products_to_display}
        products_to_display = list(set(products_to_display) - set(session.filter_local_data(models_to_filter)['product.template']))
        self.assertEqual(products_to_display, [product3.id])

        # No change
        products_to_display = [product3.id, product4.id]
        models_to_filter = {'product.template': products_to_display}
        products_to_display = list(set(products_to_display) - set(session.filter_local_data(models_to_filter)['product.template']))
        self.assertEqual(sorted(products_to_display), sorted([product3.id, product4.id]))

        # Delete all products
        products_to_display = [product3.id, product4.id]
        product3.unlink()
        product4.unlink()
        models_to_filter = {'product.template': products_to_display}
        products_to_display = list(set(products_to_display) - set(session.filter_local_data(models_to_filter)['product.template']))
        self.assertEqual(products_to_display, [])

        # Cannot archive config while session is active
        with self.assertRaises(UserError):
            config.write({'active': False})

    def test_load_data_response_structure(self):
        """load_data() must return fields, relations, dependencies and records for every model."""
        session = self.open_new_session(config=self.pos_config_usd)
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
        session = self.open_new_session(config=self.pos_config_usd)
        data = session.load_data()

        self.assertIn('pos.session', data)
        self.assertIn('pos.config', data)
        self.assertTrue(data['pos.session']['records'],
            "pos.session should have at least one record")
        self.assertTrue(data['pos.config']['records'],
            "pos.config should have at least one record")

    def test_load_data_relations_contain_relational_fields(self):
        """Relations metadata must include many2one/one2many/many2many field entries."""
        session = self.open_new_session(config=self.pos_config_usd)
        data = session.load_data()

        product_relations = data['product.product']['relations']
        relational_types = {v['type'] for v in product_relations.values()}
        self.assertTrue(
            relational_types & {'many2one', 'one2many', 'many2many'},
            "product.product relations should contain relational field types"
        )

    def test_load_data_relations_many2one_has_ondelete(self):
        """Many2one relation entries should carry the ondelete attribute when set."""
        session = self.open_new_session(config=self.pos_config_usd)
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
        session = self.open_new_session(config=self.pos_config_usd)
        data = session.load_data({'only_records': True})

        self.assertTrue(data)
        for model_name, records in data.items():
            self.assertIsInstance(records, list)

    def test_load_data_only_records_contains_session(self):
        """only_records=True must still include pos.session and pos.config records."""
        session = self.open_new_session(config=self.pos_config_usd)
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
        session = self.open_new_session(config=self.pos_config_usd)
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
        session = self.open_new_session(config=self.pos_config_usd)
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
        """Records whose local timestamp is in the future should not be returned except PosConfig."""
        session = self.open_new_session(config=self.pos_config_usd)
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
        self.assertTrue(result.get('pos.config'),
            "pos.config should always be reloaded, even if the local copy is up to date")

        product_records = full_data['product.product']
        self.assertTrue(product_records)

        product_timestamps = {
            str(record['id']): fields.Datetime.from_string(record['write_date']).timestamp()
            for record in product_records
        }

        result = session.load_data({
            'models': ['product.product'],
            'records': {'product.product': product_timestamps},
            'only_records': True,
        })
        self.assertEqual(result.get('product.product', []), [],
            "Up-to-date record should be skipped in incremental load")

    def test_load_data_incremental_returns_outdated_records(self):
        """Records with a local timestamp of 0 (never synced) must always be returned."""
        session = self.open_new_session(config=self.pos_config_usd)
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
        category = self.env['pos.category'].create({'name': 'Temp Category'})
        deleted_id = category.id
        category.unlink()
        session = self.open_new_session(config=self.pos_config_usd)

        data = session.load_data({
            'records': {'pos.category': {str(deleted_id): 0}},
        })
        to_remove = data.get('pos.category', {}).get('to_remove', [])
        self.assertIn(deleted_id, to_remove,
            "Deleted record ID should be listed in to_remove")

    def test_load_data_to_remove_deactivated_record(self):
        """Deactivated (active=False) record IDs should also appear in to_remove."""
        session = self.open_new_session(config=self.pos_config_usd)

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
        session = self.open_new_session(config=self.pos_config_usd)
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
        session = self.open_new_session(config=self.pos_config_usd)
        fake_id = 999999999

        result = session.filter_local_data({'pos.category': [str(fake_id)]})
        self.assertIn('pos.category', result)
        self.assertIn(fake_id, result['pos.category'],
            "Non-existent ID should be returned by filter_local_data")

    def test_filter_local_data_does_not_return_existing_ids(self):
        """filter_local_data should not return IDs that exist and are active."""
        session = self.open_new_session(config=self.pos_config_usd)
        full_data = session.load_data({'only_records': True})
        config_id = full_data['pos.config'][0]['id']

        result = session.filter_local_data({'pos.config': [str(config_id)]})
        ids_to_remove = result.get('pos.config', [])
        self.assertNotIn(config_id, ids_to_remove,
            "Existing active record should not be returned by filter_local_data")

    def test_filter_local_data_handles_model_no_longer_in_registry(self):
        """filter_local_data should not crash on a model that no longer exists (e.g. its
        module was uninstalled since the client last synced), and should treat all of its
        locally cached IDs as stale."""
        session = self.open_new_session(config=self.pos_config_usd)

        result = session.filter_local_data({'this.model.does.not.exist': ['1', '2']})

        self.assertEqual(sorted(result.get('this.model.does.not.exist', [])), [1, 2],
            "IDs of a model missing from the registry should all be treated as stale")

    # -------------------------------------------------------------------------
    # Pagination via search_params
    # -------------------------------------------------------------------------

    def test_load_data_search_params_limit(self):
        """search_params limit should cap the number of records returned."""
        session = self.open_new_session(config=self.pos_config_usd)
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
        session = self.open_new_session(config=self.pos_config_usd)

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

    def test_pos_loaded_product_taxes_on_branch(self):
        """ Check loaded product taxes on branch company """
        # create the following branch hierarchy:
        #     Parent company
        #         |----> Branch X
        #                   |----> Branch XX
        company = self.pos_config_usd.company_id
        branch_x = self.env['res.company'].create({
            'name': 'Parent Company',
            'country_id': company.country_id.id,
            'parent_id': company.id,
        })
        branch_xx = self.env['res.company'].create({
            'name': 'Branch XX',
            'country_id': company.country_id.id,
            'parent_id': branch_x.id,
        })
        self.cr.precommit.run()  # load the CoA
        # create taxes for the parent company and its branches
        tax_groups = self.env['account.tax.group'].create([{
            'name': 'Tax Group',
            'company_id': company.id,
        }, {
            'name': 'Tax Group X',
            'company_id': branch_x.id,
        }, {
            'name': 'Tax Group XX',
            'company_id': branch_xx.id,
        }])
        tax_a = self.env['account.tax'].create({
            'name': 'Tax A',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 10,
            'tax_group_id': tax_groups[0].id,
            'company_id': company.id,
        })
        tax_b = self.env['account.tax'].create({
            'name': 'Tax B',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 15,
            'tax_group_id': tax_groups[0].id,
            'company_id': company.id,
        })
        tax_x = self.env['account.tax'].create({
            'name': 'Tax X',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 20,
            'tax_group_id': tax_groups[1].id,
            'company_id': branch_x.id,
        })
        tax_xx = self.env['account.tax'].create({
            'name': 'Tax XX',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 25,
            'tax_group_id': tax_groups[2].id,
            'company_id': branch_xx.id,
        })
        # create several products with different taxes combination
        product_all_taxes = self.env['product.product'].create({
            'name': 'Product all taxes',
            'available_in_pos': True,
            'taxes_id': [odoo.Command.set((tax_a + tax_b + tax_x + tax_xx).ids)],
        })
        product_no_xx_tax = self.env['product.product'].create({
            'name': 'Product no tax from XX',
            'available_in_pos': True,
            'taxes_id': [odoo.Command.set((tax_a + tax_b + tax_x).ids)],
        })
        product_no_branch_tax = self.env['product.product'].create({
            'name': 'Product no tax from branch',
            'available_in_pos': True,
            'taxes_id': [odoo.Command.set((tax_a + tax_b).ids)],
        })
        product_no_tax = self.env['product.product'].create({
            'name': 'Product no tax',
            'available_in_pos': True,
            'taxes_id': [],
        })
        # configure a session on Branch XX
        self.xx_bank_journal = self.env['account.journal'].with_company(branch_xx).create({
            'name': 'Bank',
            'type': 'bank',
            'company_id': branch_xx.id,
            'code': 'BNK',
            'sequence': 15,
        })
        xx_config = self.env['pos.config'].with_company(branch_xx).create({
            'name': 'Branch XX config',
            'company_id': branch_xx.id,
        })
        xx_account_receivable = self.company_data['default_account_receivable'].copy({'company_ids': [Command.set(branch_xx.ids)]})
        xx_cash_journal = self.company_data['default_journal_cash'].copy({'company_id': branch_xx.id})
        xx_cash_payment_method = self.env['pos.payment.method'].create({
            'name': 'XX Cash Payment',
            'type': 'cash',
            'receivable_account_id': xx_account_receivable.id,
            'journal_id': xx_cash_journal.id,
            'company_id': branch_xx.id,
        })
        xx_config.write({'payment_method_ids': [
            odoo.Command.set(xx_cash_payment_method.ids),
        ]})
        pos_session = self.open_new_session(config=xx_config)
        # load the session data from Branch XX:
        # - Product all taxes           => tax from Branch XX should be set
        # - Product no tax from XX      => tax from Branch X should be set
        # - Product no tax from branch  => 2 taxes from parent company should be set
        # - Product no tax              => no tax should be set
        pos_data = pos_session.load_data()
        self.assertEqual(
            next(iter(filter(lambda p: p['id'] == product_all_taxes.product_tmpl_id.id, pos_data['product.template']['records'])))['taxes_id'],
            tax_xx.ids
        )
        self.assertEqual(
            next(iter(filter(lambda p: p['id'] == product_no_xx_tax.product_tmpl_id.id, pos_data['product.template']['records'])))['taxes_id'],
            tax_x.ids
        )
        tax_data_no_branch = next(iter(filter(lambda p: p['id'] == product_no_branch_tax.product_tmpl_id.id, pos_data['product.template']['records'])))['taxes_id']
        tax_data_no_branch.sort()
        self.assertEqual(
            tax_data_no_branch,
            (tax_a + tax_b).ids
        )
        self.assertEqual(
            next(iter(filter(lambda p: p['id'] == product_no_tax.product_tmpl_id.id, pos_data['product.template']['records'])))['taxes_id'],
            []
        )

        pos_user = self.env['res.users'].create({
            'name': 'Joe Odoo',
            'login': 'pos_user',
            'password': 'pos_user',
            'group_ids': [
                (4, self.env.ref('base.group_user').id),
                (4, self.env.ref('point_of_sale.group_pos_user').id),
            ],
            'tz': 'America/New_York',
            'company_id': branch_xx.id,
            'company_ids': [Command.set([company.id, branch_x.id, branch_xx.id])],
        })

        def get_taxes_name_popup(product):
            product = product.product_tmpl_id
            # In order to simulate the state of the cache when we run this
            # function over RPC, we need to fetch the below data first,
            # invalidate our cache, and then enter `get_product_info_pos`
            # with the arguments already loaded. This is necessary to test
            # an access rights issue when trying to load product info.
            branch_xx_id = branch_xx.id
            xx_config_id = xx_config.id
            product_all_taxes_lst_price = product_all_taxes.lst_price
            self.env.invalidate_all()
            return [tax['name'] for tax in product.with_user(pos_user).with_context(allowed_company_ids=[branch_xx_id]).get_product_info_pos(product_all_taxes_lst_price, 1, xx_config_id)['all_prices']['tax_details']]

        self.assertEqual(get_taxes_name_popup(product_all_taxes), ["Tax XX"])
        self.assertEqual(get_taxes_name_popup(product_no_xx_tax), ["Tax X"])
        self.assertEqual(get_taxes_name_popup(product_no_branch_tax), ["Tax A", "Tax B"])
        self.assertEqual(get_taxes_name_popup(product_no_tax), [])

    def test_get_product_info_pos_with_fiscal_position(self):
        tax_15 = self.env['account.tax'].create({
            'name': 'tax_15',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 15.0,
        })
        tax_30 = self.env['account.tax'].create({
            'name': 'tax_30',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 30.0,
            'original_tax_ids': [Command.set(tax_15.ids)],
        })
        fp = self.env['account.fiscal.position'].create({
            'name': 'Maps 15 to 30',
            'tax_ids': [Command.set(tax_30.ids)],
        })
        product = self.create_product('Product FP', 100.0, tax_15.ids)
        template = product.product_tmpl_id

        def get_display_info(fp_id=False):
            info = template.with_context(fiscal_position_id=fp_id).get_product_info_pos(100.0, 1, self.pos_config_usd.id)['all_prices']
            return (info['price_with_tax'], [t['name'] for t in info['tax_details']])

        self.assertEqual(get_display_info(), (115.0, ['tax_15']))
        self.assertEqual(get_display_info(fp.id), (130.0, ['tax_30']))

    def test_combo_product_variant_error(self):
        """This tests make sure that product containing variants cannot change type to combo"""

        size_attribute = self.env['product.attribute'].create({'name': 'Size'})
        a1 = self.env['product.attribute.value'].create({'name': 'V0hFCg==', 'attribute_id': size_attribute.id})
        self.variant_product = self.env["product.product"].create(
            {
                "name": "Test product",
                "attribute_line_ids": [(0, 0, {
                    "attribute_id": size_attribute.id,
                    "value_ids": [(6, 0, [a1.id])]
                })],
            })
        with self.assertRaises(UserError):
            with Form(self.variant_product.product_tmpl_id) as product:
                product.type = "combo"

    def test_product_combo_variants(self):
        # Add attribute and values, simulating variant creation
        product_combo = self.env['product.combo'].create({
            'name': 'Product combo',
            'combo_item_ids': [Command.create({'product_id': self.product.id})],
        })
        size_attribute = self.env.ref('product.pa_size')
        original_product_id = self.product.id
        self.product.product_tmpl_id.with_context(create_product_product=True).write({
            'attribute_line_ids': [(0, 0, {
                'attribute_id': size_attribute.id,
                'value_ids': [
                    Command.create({'name': 'Large', 'attribute_id': size_attribute.id}),
                    Command.create({'name': 'Small', 'attribute_id': size_attribute.id}),
                ],
            })],
        })
        # Check that original product should not be in combo anymore (replace by variants)
        self.assertTrue(
            original_product_id not in product_combo.combo_item_ids.mapped('product_id').ids,
            'Original product should not be in combo'
        )
