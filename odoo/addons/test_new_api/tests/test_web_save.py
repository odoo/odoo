# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import TransactionCase


class TestWebSave(TransactionCase):

    def test_web_save_create(self):
        ''' Test the web_save method on a new record. '''
        # Create a new record, without unity specification (it should return only the id)
        self.env['test_new_api.person'].search([]).unlink()
        result = self.env['test_new_api.person'].web_save({'name': 'ged'}, {})
        person = self.env['test_new_api.person'].search([])
        self.assertTrue(person.exists())
        self.assertEqual(person.name, 'ged')
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [{'id': person.id}])

        # Create a new record, with unity specification
        result = self.env['test_new_api.person'].web_save({'name': 'ged'}, {'display_name': {}})
        person = self.env['test_new_api.person'].browse(result[0]['id'])
        self.assertTrue(person.exists())
        self.assertEqual(result, [{'id': person.id, 'display_name': 'ged'}])


    def test_web_save_write(self):
        ''' Test the web_save method on an existing record. '''

        person = self.env['test_new_api.person'].create({'name': 'ged'})

        # Modify an existing record, without unity specification (it should return only the id)
        result = person.web_save({'name': 'aab'}, {})
        self.assertEqual(person.name, 'aab')
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [{'id': person.id}])

        # Modify an existing record, with unity specification
        result = person.web_save({'name': 'lpe'}, {'display_name': {}})
        self.assertEqual(result, [{'id': person.id, 'display_name': 'lpe'}])
