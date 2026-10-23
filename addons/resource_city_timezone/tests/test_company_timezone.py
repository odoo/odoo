# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCompanyTimezone(TransactionCase):

    def test_company_timezone(self):
        company = self.env['res.company'].with_context(tz='Asia/Tokyo').create({
            'name': 'Seattle Company',
            'country_id': self.env.ref('base.us').id,
            'city': 'Seattle',
        })
        self.assertEqual(company.tz, 'America/Los_Angeles')
        company.city = 'El Paso'
        self.assertEqual(company.tz, 'America/Denver')
        # unknown city: falls back on the context's timezone
        company.city = 'Nowhere Town'
        self.assertEqual(company.tz, 'Asia/Tokyo')
        # single-timezone country: no city needed
        company.write({'country_id': self.env.ref('base.be').id, 'city': False})
        self.assertEqual(company.tz, 'Europe/Brussels')
