from unittest.mock import patch

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestWebSaveOffline(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country = cls.env.ref('base.be')
        cls.parent = cls.env['res.partner'].create({
            'name': 'Parent',
            'street': 'Main street',
            'city': 'Brussels',
            'country_id': cls.country.id,
        })
        cls.spec = {'street': {}, 'city': {}, 'country_id': {'fields': {'display_name': {}}}}
        cls.fields_to_save = ['name', 'parent_id', 'street', 'city', 'country_id', 'child_ids']

    def _web_save_offline(self, vals, onchange_spec=None, changed_fields=None):
        [result] = self.env['res.partner'].web_save_offline(
            vals, ['parent_id'], vals, self.spec if onchange_spec is None else onchange_spec,
            changed_fields or ['name', 'parent_id'], self.fields_to_save,
        )
        return self.env['res.partner'].browse(result['id'])

    def test_onchange_values_are_saved(self):
        partner = self._web_save_offline({'name': 'Child', 'parent_id': self.parent.id})
        self.assertEqual(partner.parent_id, self.parent)
        self.assertEqual(partner.street, 'Main street')
        self.assertEqual(partner.city, 'Brussels')
        self.assertEqual(partner.country_id, self.country)

    def test_onchange_is_called_with_the_values_with_readonly(self):
        Partner = self.env['res.partner']
        result = {'value': {'street': 'From onchange'}}
        vals = {'name': 'Child', 'parent_id': self.parent.id}
        vals_w_readonly = {**vals, 'ref': 'Readonly'}
        with patch.object(self.registry['res.partner'], 'onchange', return_value=result) as onchange:
            [saved] = Partner.web_save_offline(
                vals, ['parent_id'], vals_w_readonly, self.spec, ['parent_id'],
                self.fields_to_save,
            )
        onchange.assert_called_once_with(vals_w_readonly, ['parent_id'], self.spec)
        self.assertEqual(Partner.browse(saved['id']).street, 'From onchange')
        self.assertFalse(Partner.browse(saved['id']).ref)

    def test_existing_record(self):
        partner = self.env['res.partner'].create({'name': 'Child'})
        partner.web_save_offline(
            {'parent_id': self.parent.id}, ['parent_id'], {'parent_id': self.parent.id}, self.spec,
            ['parent_id'], self.fields_to_save,
        )
        self.assertEqual(partner.street, 'Main street')

    def test_onchange_replaces_the_empty_values_of_a_new_record(self):
        # a new record sends an explicit empty value for the fields it did not touch
        Partner = self.env['res.partner']
        result = {'value': {'street': 'From onchange'}}
        with patch.object(self.registry['res.partner'], 'onchange', return_value=result):
            [saved] = Partner.web_save_offline(
                {'name': 'Child', 'parent_id': self.parent.id, 'street': False},
                ['parent_id'], {'name': 'Child', 'parent_id': self.parent.id, 'street': False}, self.spec,
                ['name', 'parent_id'], self.fields_to_save,
            )
        self.assertEqual(Partner.browse(saved['id']).street, 'From onchange')

    def test_values_of_the_user_are_kept(self):
        partner = self._web_save_offline({
            'name': 'Child',
            'parent_id': self.parent.id,
            'street': 'My street',
        }, changed_fields=['name', 'parent_id', 'street'])
        self.assertEqual(partner.street, 'My street')
        self.assertEqual(partner.city, 'Brussels')

    def test_only_the_specified_fields_are_saved(self):
        partner = self._web_save_offline(
            {'name': 'Child', 'parent_id': self.parent.id},
            onchange_spec={'street': {}},
        )
        self.assertEqual(partner.street, 'Main street')
        self.assertFalse(partner.city)

    def test_without_onchange_fields(self):
        Partner = self.env['res.partner']
        with patch.object(self.registry['res.partner'], 'onchange') as onchange:
            Partner.web_save_offline({'name': 'Child'}, [], {}, {}, [], [])
        onchange.assert_not_called()

    def test_changed_fields_are_not_taken_from_the_onchange(self):
        Partner = self.env['res.partner']
        result = {'value': {'street': 'From onchange', 'city': 'From onchange'}}
        with patch.object(self.registry['res.partner'], 'onchange', return_value=result):
            [saved] = Partner.web_save_offline(
                {'name': 'Child', 'city': 'Mine'}, ['name'], {'name': 'Child', 'city': 'Mine'},
                self.spec, ['city'], self.fields_to_save,
            )
        self.assertEqual(Partner.browse(saved['id']).street, 'From onchange')
        self.assertEqual(Partner.browse(saved['id']).city, 'Mine')

    def test_x2many_with_a_value_is_not_replaced(self):
        Partner = self.env['res.partner']
        result = {'value': {'child_ids': [(1, 'virtual_1', {'name': 'From onchange'})]}}
        with patch.object(self.registry['res.partner'], 'onchange', return_value=result):
            [saved] = Partner.web_save_offline(
                {'name': 'Parent', 'child_ids': [(0, 'virtual_1', {'name': 'Mine'})]},
                ['name'], {'name': 'Parent'}, {}, [], self.fields_to_save,
            )
        self.assertEqual(Partner.browse(saved['id']).child_ids.mapped('name'), ['Mine'])

    def test_onchange_without_value(self):
        Partner = self.env['res.partner']
        with patch.object(self.registry['res.partner'], 'onchange', return_value={}):
            [saved] = Partner.web_save_offline({'name': 'Child'}, ['name'], {'name': 'Child'}, {}, [], [])
        self.assertEqual(Partner.browse(saved['id']).name, 'Child')

    def test_fields_not_saved_by_the_view_are_not_taken_from_the_onchange(self):
        Partner = self.env['res.partner']
        result = {'value': {'street': 'From onchange', 'city': 'From onchange'}}
        with patch.object(self.registry['res.partner'], 'onchange', return_value=result):
            [saved] = Partner.web_save_offline(
                {'name': 'Child'}, ['name'], {'name': 'Child'}, self.spec, [], ['street'],
            )
        self.assertEqual(Partner.browse(saved['id']).street, 'From onchange')
        self.assertFalse(Partner.browse(saved['id']).city)

    def test_many2one_values_of_the_lines_are_written_as_ids(self):
        Partner = self.env['res.partner']
        country = {'id': self.country.id, 'display_name': self.country.display_name}
        lines = [(0, 'virtual_1', {'name': 'Line', 'country_id': country})]
        with patch.object(self.registry['res.partner'], 'onchange', return_value={'value': {'child_ids': lines}}):
            [saved] = Partner.web_save_offline(
                {'name': 'Parent'}, ['name'], {'name': 'Parent'}, {}, [], ['child_ids'],
            )
        [child] = Partner.browse(saved['id']).child_ids
        self.assertEqual(child.name, 'Line')
        self.assertEqual(child.country_id, self.country)
