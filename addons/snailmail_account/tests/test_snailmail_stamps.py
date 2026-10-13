# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSnailmailStamps(TransactionCase):
    """ The number of stamps shown in the Send & Print summary must be the number of
    letters the batch actually sends, since the IAP service charges one stamp per letter.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.address = {
            'street': 'Test street',
            'zip': '12345',
            'city': 'Testcity',
            'country_id': cls.env.ref('base.be').id,
        }
        cls.partner = cls.env['res.partner'].create({
            'name': 'Snailmail Customer',
            'invoice_sending_method': 'snailmail',
            **cls.address,
        })

    def _create_invoice(self, partner=None):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': (partner or self.partner).id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [Command.create({
                'name': 'Test line',
                'quantity': 1,
                'price_unit': 100.0,
            })],
        })
        invoice.action_post()
        return invoice

    def _assert_shown_stamps_match_letters_sent(self, invoices):
        """ Send the batch and check the summary announced as many stamps as the number
        of letters that were created.
        """
        wizard = self.env['account.move.send.batch.wizard'].create({
            'move_ids': [Command.set(invoices.ids)],
        })
        shown_stamps = wizard.summary_data['snailmail'].get('extra')

        letters_before = self.env['snailmail.letter'].search_count([])
        wizard.action_send_and_print(force_synchronous=True)
        letters_sent = self.env['snailmail.letter'].search_count([]) - letters_before

        self.assertEqual(shown_stamps, '(Stamps: %s)' % letters_sent)
        return letters_sent

    def test_stamps_shown_for_several_invoices_of_one_customer(self):
        """ Two invoices to the same customer are two letters, hence two stamps. """
        invoices = self._create_invoice() | self._create_invoice()

        self.assertEqual(self._assert_shown_stamps_match_letters_sent(invoices), 2)

    def test_stamps_shown_ignore_other_sending_methods(self):
        """ Only the invoices actually sent by post cost a stamp, even when the other
        recipients have an address a letter could have been sent to.
        """
        by_email_partner = self.env['res.partner'].create({
            'name': 'Email Customer',
            'email': 'email.customer@example.com',
            'invoice_sending_method': 'email',
            **self.address,
        })
        invoices = self._create_invoice() | self._create_invoice(partner=by_email_partner)

        self.assertEqual(self._assert_shown_stamps_match_letters_sent(invoices), 1)
