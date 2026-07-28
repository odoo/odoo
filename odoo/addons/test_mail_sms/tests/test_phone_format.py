from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('phone_validation')
class TestPhoneFormat(TransactionCase):

    def test_phone_format_country_guess(self):
        # based on partner country
        partners = self.env['res.partner'].create([
            {'name': 'Alex Bell', 'country_id': self.env.ref('base.us').id},
            {'name': 'Elie Grey', 'country_id': self.env.ref('base.uk').id},
        ])
        test_record = self.env['mail.test.sms'].create({
            'country_id': False,
            'name': 'Record for Context',
            'customer_id': False,
        })
        base_partner_vals = [
            {'country_id': self.env.ref('base.us').id},
            {'country_id': self.env.ref('base.uk').id},
        ]
        base_record_vals = {
            'country_id': False,
            'customer_id': False,
            'guest_ids': False,
        }
        partner_vals_all = [({}, {}), ({}, {}), ({'country_id': False}, {}), ({}, {'country_id': False}), ({}, {})]
        record_vals_all = [
            {'customer_id': partners[0].id}, {'guest_ids': partners}, {'guest_ids': partners},
            {'country_id': partners[1].country_id.id, 'customer_id': partners[1].id},
            {'country_id': partners[1].country_id.id},
        ]
        input_numbers = ['251 842 8701', '251 842 8701', '078 9216 4126', '078 9216 4126', '+32499000000']
        expected_numbers = ['+12518428701', '+12518428701', '+447892164126', '+447892164126', '+32499000000']
        test_names = ['customer country', 'first guest country', 'second guest country', 'record country', 'existing prefix']

        for partner_vals, record_vals, input_number, expected_number, test_name in zip(partner_vals_all, record_vals_all, input_numbers, expected_numbers, test_names):
            for partner, base_vals, vals in zip(partners, base_partner_vals, partner_vals):
                partner.write(base_vals | vals)
            test_record.write(base_record_vals | record_vals)
            with self.subTest(test_name=test_name):
                self.assertEqual(
                    test_record._phone_format(
                        number=input_number,
                    ), expected_number)

    def test_phone_format_perf(self):
        PARTNER_COUNT = 100

        countries = self.env['res.country'].create([{
            'name': f'Test Country {n}',
            'code': str(n),
        } for n in range(20)])

        country_partners = self.env['res.partner'].create([
            {'name': f'{countries[_id % len(countries)].name} partner', 'country_id': countries[_id % len(countries)].id}
            for _id in range(PARTNER_COUNT)
        ])

        nocountry_partners = self.env['res.partner'].create([
            {'name': 'Countryless Man', 'country_id': False}
            for _ in range(PARTNER_COUNT)
        ])

        test_records = self.env['mail.test.sms'].create([{
            'country_id': False,
            'name': 'Phone Format Test Record',
            'customer_id': nocountry_p.id,
            'guest_ids': country_p.ids,
        } for nocountry_p, country_p in zip(nocountry_partners, country_partners)])

        test_records.invalidate_recordset()
        (country_partners + nocountry_partners).invalidate_recordset()
        countries.invalidate_recordset()
        # 1 query per country + 4
        with self.assertQueryCount(24):
            for record in test_records:
                record._phone_format(
                    number='078 9216 4126',
                    raise_exception=False,
                )
