# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_renting.tests.common import SaleRentingCommon


class TestWebsiteSaleRentingCommon(SaleRentingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'Renting Company',
            'renting_forbidden_sat': True,
            'renting_forbidden_sun': True,
        })
        cls.website = cls.env['website'].create({
            'name': 'Test website',
            'company_id': cls.company.id,
            'tz': 'Europe/Brussels',
        })
        cls.website_2 = cls.env['website'].create({
            'name': 'Test website 2',
            'company_id': cls.company.id,
            'tz': 'America/New_York',
        })
        cls.computer = cls.env['product.product'].create({
            'name': 'Computer',
            'list_price': 2000,
            'rent_ok': True,
        })
        recurrence_5_hour = cls.env['sale.temporal.recurrence'].sudo().create({'duration': 5, 'unit': 'hour'})
        cls.env['product.pricing'].create([
            {
                'recurrence_id': cls.recurrence_hour.id,
                'price': 3.5,
                'product_template_id': cls.computer.product_tmpl_id.id,
            }, {
                'recurrence_id': recurrence_5_hour.id,
                'price': 15.0,
                'product_template_id': cls.computer.product_tmpl_id.id,
            },
        ])
        cls.partner = cls.env['res.partner'].create({
            'name': 'partner_a',
        })

    def setUp(self):
        super().setUp()
        # Allow renting on any day for tests, avoids unexpected error
        self.env.company.renting_forbidden_mon = False
        self.env.company.renting_forbidden_tue = False
        self.env.company.renting_forbidden_wed = False
        self.env.company.renting_forbidden_thu = False
        self.env.company.renting_forbidden_fri = False
        self.env.company.renting_forbidden_sat = False
        self.env.company.renting_forbidden_sun = False
