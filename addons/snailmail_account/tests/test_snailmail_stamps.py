# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSnailmailStamps(TransactionCase):
    """ The stamps announced by the Send & Print wizard must match what IAP bills, which
    is the number of pages of the letters, one letter being created per invoice.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.snailmail_cover = False
        cls.company.snailmail_duplex = False
        cls.partner = cls.env['res.partner'].create({
            'name': 'Snailmail Customer',
            'street': 'Test street',
            'zip': '12345',
            'city': 'Testcity',
            'country_id': cls.env.ref('base.be').id,
            'invoice_sending_method': 'snailmail',
        })

    def _create_invoice(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
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

    def test_stamps_count_the_cover_page(self):
        """ The cover page, and its blank backside in duplex, are extra pages. """
        invoice = self._create_invoice()
        self.assertEqual(self._announced_stamps(invoice), 1)

        self.company.snailmail_cover = True
        self.assertEqual(self._announced_stamps(invoice), 2)

        self.company.snailmail_duplex = True
        self.assertEqual(self._announced_stamps(invoice), 3)

    def test_stamps_count_one_letter_per_invoice(self):
        """ One letter is created per invoice, even when they share the same recipient. """
        invoices = self._create_invoice() | self._create_invoice()
        self.assertEqual(self._announced_stamps(invoices), 2)
