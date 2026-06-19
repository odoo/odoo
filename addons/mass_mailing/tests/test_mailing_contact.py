# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mass_mailing.tests.common import MassMailCommon


class TestMailingContact(MassMailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Prepare
        cls.env['mailing.contact'].search([('email', '=', False)]).unlink()
        cls.contacts = cls.env['mailing.contact'].create([
            {'name': 'Contact One', 'email': 'contact.one@company.com'},
            {'name': 'Contact Two', 'email': 'contact.two@company.com'},
            {'name': 'Contact Three', 'email': 'contact.three@company.com'},
            {'name': 'Contact Four', 'email': 'contact.four@company.com'}
        ])
        cls.traces = cls.env['mailing.trace'].create([
            {
                'trace_type': 'mail',
                'model': 'mailing.contact',
                'res_id': cls.contacts[0].id,
            },
            {
                'trace_type': 'mail',
                'model': 'mailing.contact',
                'res_id': cls.contacts[0].id,
            },
            {
                'trace_type': 'mail',
                'model': 'mailing.contact',
                'res_id': cls.contacts[1].id,
            },
            {
                'trace_type': 'mail',
                'model': 'mailing.contact',
                'res_id': cls.contacts[1].id,
            },
            {
                'trace_type': 'mail',
                'model': 'mailing.contact',
                'res_id': cls.contacts[2].id,
            },
        ])
        for trace in cls.traces:
            trace.set_sent()

    def test_compute_mailing_count(self):
        # Prepare
        test_params = [
            # (contact, expected)
            (self.contacts[0], 2),
            (self.contacts[1], 2),
            (self.contacts[2], 1),
            (self.contacts[3], 0)
        ]
        # Execute & assert
        for contact, expected in test_params:
            self.assertEqual(expected, contact.mailing_count)
