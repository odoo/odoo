from odoo.tests import common


class TestInheritsOnchange(common.TransactionCase):

    def test_onchange_reselect_delegate_after_clearing(self):
        """ Clearing the delegate Many2one and re-selecting the same parent record must not
        leave the inherited field stuck on the blank value from the cleared state. """
        unit = self.env['test.unit'].create({'name': 'Foo'})
        box = self.env['test.box'].create({'unit_id': unit.id, 'field_in_box': 'box'})
        fields_spec = {'unit_id': {}, 'name': {}}

        # Clear the delegate field: the inherited field goes blank, as expected.
        result = box.onchange({'unit_id': False, 'name': box.name}, ['unit_id'], fields_spec)
        self.assertEqual(result['value'].get('name'), False)

        # Re-select the *same* unit: the inherited field must reflect its real value again.
        result = box.onchange({'unit_id': unit.id, 'name': False}, ['unit_id'], fields_spec)
        self.assertEqual(result['value'].get('name'), 'Foo')
