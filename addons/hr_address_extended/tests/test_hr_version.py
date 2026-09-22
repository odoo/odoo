from odoo.tests import Form, TransactionCase


class TestHrVersion(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country = cls.env.ref('base.us')
        cls.country.enforce_cities = True
        cls.state = cls.env['res.country.state'].create({
            'name': 'Kiwi Land',
            'code': 'KWL',
            'country_id': cls.country.id,
        })
        cls.city = cls.env['res.city'].create({
            'name': 'Kiwi center',
            'country_id': cls.country.id,
            'state_id': cls.state.id,
            'zipcode': '88800',
        })

    # Testing the form fields correctly populate even before saving (onchange triggers as expected):
    # 1. New employee form (no record)
    def test_onchange_private_city_id_fills_state_new_employee(self):
        with Form(self.env['hr.employee']) as employee_form:
            employee_form.name = 'Marzia'
            employee_form.private_country_id = self.country
            employee_form.private_city_id = self.city
            self.assertEqual(employee_form.private_state_id, self.state)
            self.assertEqual(employee_form.private_city, self.city.name)
            self.assertEqual(employee_form.private_zip, self.city.zipcode)

    # 2. Changes to existing employee through form (not yet saved)
    def test_onchange_private_city_id_fills_state_existing_employee(self):
        employee = self.env['hr.employee'].create({
            'name': 'Felix',
            'private_country_id': self.country.id,
        })
        with Form(employee) as employee_form:
            employee_form.private_city_id = self.city
            self.assertEqual(employee_form.private_state_id, self.state)
            self.assertEqual(employee_form.private_city, self.city.name)
            self.assertEqual(employee_form.private_zip, self.city.zipcode)

    # regression test: the write() path should correctly trigger _inverse_private_city_id()
    def test_write_private_city_id_fills_state(self):
        employee = self.env['hr.employee'].create({'name': 'Edgar'})
        employee.private_city_id = self.city
        self.assertEqual(employee.private_state_id, self.state)
        self.assertEqual(employee.private_city, self.city.name)
        self.assertEqual(employee.private_zip, self.city.zipcode)
