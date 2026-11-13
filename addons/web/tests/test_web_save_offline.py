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

    def _web_save_offline(self, vals, onchange_spec=None, changed_fields=None):
        [result] = self.env['res.partner'].web_save_offline(
            vals, {'id': {}}, ['parent_id'], self.spec if onchange_spec is None else onchange_spec,
            changed_fields or ['name', 'parent_id'],
        )
        return self.env['res.partner'].browse(result['id'])

    def test_onchange_values_are_saved(self):
        partner = self._web_save_offline({'name': 'Child', 'parent_id': self.parent.id})
        self.assertEqual(partner.parent_id, self.parent)
        self.assertEqual(partner.street, 'Main street')
        self.assertEqual(partner.city, 'Brussels')
        self.assertEqual(partner.country_id, self.country)

    def test_onchange_is_called_with_the_values_and_fields(self):
        Partner = self.env['res.partner']
        result = {'value': {'street': 'From onchange'}}
        with patch.object(self.registry['res.partner'], 'onchange', return_value=result) as onchange:
            [saved] = Partner.web_save_offline(
                {'name': 'Child', 'parent_id': self.parent.id}, {'street': {}}, ['parent_id'], self.spec, ['parent_id'],
            )
        onchange.assert_called_once_with({'name': 'Child', 'parent_id': self.parent.id}, ['parent_id'], self.spec)
        self.assertEqual(saved['street'], 'From onchange')

    def test_existing_record(self):
        partner = self.env['res.partner'].create({'name': 'Child'})
        partner.web_save_offline({'parent_id': self.parent.id}, {'id': {}}, ['parent_id'], self.spec, ['parent_id'])
        self.assertEqual(partner.street, 'Main street')

    def test_onchange_replaces_the_empty_values_of_a_new_record(self):
        # a new record sends an explicit empty value for the fields it did not touch
        Partner = self.env['res.partner']
        result = {'value': {'street': 'From onchange'}}
        with patch.object(self.registry['res.partner'], 'onchange', return_value=result):
            [saved] = Partner.web_save_offline(
                {'name': 'Child', 'parent_id': self.parent.id, 'street': False}, {'street': {}},
                ['parent_id'], self.spec, ['name', 'parent_id'],
            )
        self.assertEqual(saved['street'], 'From onchange')

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
            Partner.web_save_offline({'name': 'Child'}, {'id': {}}, [], {}, [])
        onchange.assert_not_called()

    def test_many2one_values_are_written_as_ids(self):
        Partner = self.env['res.partner']
        country = {'id': self.country.id, 'display_name': self.country.display_name}
        with patch.object(self.registry['res.partner'], 'onchange', return_value={'value': {'country_id': country}}):
            [saved] = Partner.web_save_offline(
                {'name': 'Child'}, {'country_id': {}}, ['name'], self.spec, [],
            )
        self.assertEqual(saved['country_id'], self.country.id)

    def test_x2many_lines_are_written_with_ids(self):
        Partner = self.env['res.partner']
        country = {'id': self.country.id, 'display_name': self.country.display_name}
        lines = [(0, 'virtual_1', {'name': 'Line', 'country_id': country})]
        with patch.object(self.registry['res.partner'], 'onchange', return_value={'value': {'child_ids': lines}}):
            [saved] = Partner.web_save_offline(
                {'name': 'Parent'}, {'id': {}}, ['name'], {'child_ids': {'fields': {'name': {}}}}, [],
            )
        [child] = Partner.browse(saved['id']).child_ids
        self.assertEqual(child.name, 'Line')
        self.assertEqual(child.country_id, self.country)

    def test_changed_fields_are_not_taken_from_the_onchange(self):
        Partner = self.env['res.partner']
        result = {'value': {'street': 'From onchange', 'city': 'From onchange'}}
        with patch.object(self.registry['res.partner'], 'onchange', return_value=result):
            [saved] = Partner.web_save_offline(
                {'name': 'Child', 'city': 'Mine'}, {'street': {}, 'city': {}}, ['name'], self.spec, ['city'],
            )
        self.assertEqual(saved['street'], 'From onchange')
        self.assertEqual(saved['city'], 'Mine')

    def test_reference_values_are_written_as_strings(self):
        Menu = self.env['ir.ui.menu']
        report = self.env['ir.actions.report'].search([], limit=1)
        reference = {'id': {'id': report.id, 'model': report._name}, 'display_name': report.display_name}
        with patch.object(self.registry['ir.ui.menu'], 'onchange', return_value={'value': {'action': reference}}):
            [saved] = Menu.web_save_offline({'name': 'Menu'}, {'action': {}}, ['name'], {}, [])
        self.assertEqual(Menu.browse(saved['id']).action, report)

    def test_many2one_reference_values_are_written_as_ids(self):
        Attachment = self.env['ir.attachment']
        result = {'value': {'res_id': {'id': self.parent.id, 'display_name': self.parent.display_name}}}
        with patch.object(self.registry['ir.attachment'], 'onchange', return_value=result):
            [saved] = Attachment.web_save_offline(
                {'name': 'File', 'res_model': 'res.partner'}, {'res_id': {}}, ['name'], {}, [],
            )
        self.assertEqual(saved['res_id'], self.parent.id)

    def test_x2many_with_a_value_is_not_replaced(self):
        Partner = self.env['res.partner']
        result = {'value': {'child_ids': [(1, 'virtual_1', {'name': 'From onchange'})]}}
        with patch.object(self.registry['res.partner'], 'onchange', return_value=result):
            [saved] = Partner.web_save_offline(
                {'name': 'Parent', 'child_ids': [(0, 'virtual_1', {'name': 'Mine'})]},
                {'id': {}}, ['name'], {}, [],
            )
        self.assertEqual(Partner.browse(saved['id']).child_ids.mapped('name'), ['Mine'])

    def test_onchange_without_value(self):
        Partner = self.env['res.partner']
        with patch.object(self.registry['res.partner'], 'onchange', return_value={}):
            [saved] = Partner.web_save_offline({'name': 'Child'}, {'name': {}}, ['name'], {}, [])
        self.assertEqual(saved['name'], 'Child')
