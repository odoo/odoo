# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import Form, tagged, TransactionCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestHrVersion(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country = cls.env.ref('base.us')
        cls.country.enforce_cities = True
        cls.state = cls.env['res.country.state'].create({
            'name': 'Test State',
            'code': 'TS',
            'country_id': cls.country.id,
        })
        cls.city = cls.env['res.city'].create({
            'name': 'Test City',
            'country_id': cls.country.id,
            'state_id': cls.state.id,
            'zipcode': '12345',
        })

    def test_onchange_private_city_id_fills_state(self):
        """ Picking a private city in the form should fill state/city/zip live.
        It should not need a save first, unlike the inverse-only write path. """
        with Form(self.env['hr.employee']) as employee_form:
            employee_form.name = 'Test Employee'
            employee_form.private_country_id = self.country
            employee_form.private_city_id = self.city
            self.assertEqual(employee_form.private_state_id, self.state)
            self.assertEqual(employee_form.private_zip, self.city.zipcode)

    def test_write_private_city_id_fills_state(self):
        """ The inverse (write path) keeps working as before. """
        employee = self.env['hr.employee'].create({'name': 'Test Employee'})
        employee.private_city_id = self.city
        self.assertEqual(employee.private_state_id, self.state)
        self.assertEqual(employee.private_zip, self.city.zipcode)
