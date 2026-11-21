from datetime import datetime

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_pt_certification.tests.common import TestL10nPtCommon

# Tomorrow at 08:30 UTC, 09:30 in Lisbon (summer time).
START = datetime(2026, 6, 16, 8, 30)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtInvoiceTransportDocument(TestL10nPtCommon):
    """
    An invoice may be the document its goods travel with (RBC art. 2(1)(b)): it then states the places
    of loading and unloading, referred to as such, and the date and time the transport starts (RBC art.
    4(4)). Only an invoice can be one (RBC art. 4(1)), for goods unloaded in Portugal (art. 3), and once
    issued, none of it can change.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.delivery_address = cls.make_address()

    @classmethod
    def make_address(cls, **vals):
        """A delivery address of ``partner_pt``, in Braga, over which ``vals`` are written."""
        return cls.env['res.partner'].create({
            'name': 'Armazém do Cliente',
            'type': 'delivery',
            'parent_id': cls.partner_pt.id,
            'street': 'Rua do Armazém 7',
            'city': 'Braga',
            'zip': '4700-001',
            'country_id': cls.env.ref('base.pt').id,
            **vals,
        })

    @classmethod
    def make_transport_invoice(cls, **vals):
        """A draft invoice marked as transport document, starting tomorrow, to ``delivery_address``."""
        return cls.make_invoice(**{
            'l10n_pt_is_transport_document': True,
            'l10n_pt_start_transport_date': START,
            'partner_shipping_id': cls.delivery_address.id,
            **vals,
        })

    def test_issued_and_printed_as_transport_document(self):
        """
        Marked as transport document, an invoice loads at the company's address unless told otherwise and
        unloads at its delivery address; posted with a start still to come, it is issued as any invoice,
        and its print states both places, referred to as such, and the start in Lisbon time. An invoice
        not marked prints none of it.
        """
        invoice = self.make_transport_invoice()
        self.assertEqual(invoice.l10n_pt_loading_partner_id, self.company_pt.partner_id)
        self.issue(self.post(invoice))
        self.assertIssued(invoice)

        html = self.preview(invoice)
        for text in ('Local de carga', 'Local de descarga', 'Início do transporte', '16-06-2026 09:30', 'Rua do Armazém 7'):
            self.assertIn(text, html)
        plain = self.issue(self.post(self.make_invoice()))
        self.assertNotIn('Local de carga', self.preview(plain))

    def test_refused_unless_it_can_be_one(self):
        """
        Posting refuses an invoice as transport document, saying why, when its start is missing or past,
        when it is a simplified invoice, and when a place is missing, lacks a street, city or country, or
        unloads outside Portugal.
        """
        spain = self.env.ref('base.es')
        cases = [
            ("no start", {}, {'l10n_pt_start_transport_date': False}, "no Start of Transport was entered"),
            ("past start", {}, {'l10n_pt_start_transport_date': datetime(2026, 6, 15, 9, 0)},
             "its Start of Transport, 15-06-2026 10:00, has passed"),
            ("simplified invoice", {'move_type': 'out_receipt'}, {},
             r"only an invoice \(FT, FR\) can be the transport document"),
            ("no unloading place", {}, {'partner_shipping_id': False}, "no Unloading Place was entered"),
            ("unloading without street", {'partner_shipping_id': self.make_address(street=False).id}, {},
             "its Unloading Place, .*, has no street$"),
            ("unloading without country", {'partner_shipping_id': self.make_address(country_id=False).id}, {},
             "its Unloading Place, .*, has no country$"),
            ("unloading abroad", {'partner_shipping_id': self.make_address(city='Madrid', zip='28013', country_id=spain.id).id}, {},
             "its Unloading Place is not in Portugal"),
            ("loading without address", {'l10n_pt_loading_partner_id': self.make_address(street=False, city=False).id}, {},
             "its Loading Place, .*, has no street, city$"),
        ]
        for label, create_vals, write_vals, reason in cases:
            with self.subTest(label):
                invoice = self.make_transport_invoice(**create_vals)
                invoice.write(write_vals)
                with self.assertRaisesRegex(UserError, reason), self.env.cr.savepoint():
                    self.post(invoice)
                self.assertEqual(invoice.state, 'draft')

    def test_frozen_once_issued(self):
        """
        Until it is issued, a posted transport invoice can be reset to draft and its start corrected. Once
        issued, whether it is the transport document, its places and its start cannot change, and an
        issued invoice cannot become one.
        """
        invoice = self.post(self.make_transport_invoice())
        invoice.button_draft()
        invoice.l10n_pt_start_transport_date = datetime(2026, 6, 16, 14, 0)
        self.issue(self.post(invoice))
        for field_name, value in (
            ('l10n_pt_is_transport_document', False),
            ('l10n_pt_start_transport_date', datetime(2026, 6, 17, 8, 30)),
            ('l10n_pt_loading_partner_id', self.delivery_address.id),
            ('partner_shipping_id', self.partner_pt.id),
        ):
            with self.subTest(field=field_name), self.assertRaisesRegex(UserError, "cannot be changed"), self.env.cr.savepoint():
                invoice.write({field_name: value})
        invoice.write({'l10n_pt_start_transport_date': datetime(2026, 6, 16, 14, 0)})

        plain = self.issue(self.post(self.make_invoice()))
        with self.assertRaisesRegex(UserError, "cannot be changed"), self.env.cr.savepoint():
            plain.l10n_pt_is_transport_document = True

    def test_not_copied(self):
        """A copy of a transport invoice is a plain invoice: its transport is decided again."""
        copy = self.make_transport_invoice().copy()
        self.assertFalse(copy.l10n_pt_is_transport_document)
        self.assertFalse(copy.l10n_pt_start_transport_date)
        self.assertFalse(copy.l10n_pt_loading_partner_id)
