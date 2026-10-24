# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSnailmailStamps(TransactionCase):
    """ The IAP service charges one stamp per document, and one letter is created per
    move, so the announced number of stamps is the number of invoices sent by post.
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

    def _announced_stamps(self, invoices):
        return self.env['account.move.send.batch.wizard'].create({
            'move_ids': [Command.set(invoices.ids)],
        }).send_by_post_stamps

    def test_stamps_one_per_invoice(self):
        """ Two invoices to the same customer are two letters, hence two stamps. """
        invoices = self._create_invoice() | self._create_invoice()

        self.assertEqual(self._announced_stamps(invoices), 2)

    def test_stamps_ignore_other_sending_methods(self):
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

        self.assertEqual(self._announced_stamps(invoices), 1)
