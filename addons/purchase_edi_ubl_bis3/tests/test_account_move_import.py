# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, Command

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import file_open


@tagged('post_install', '-at_install')
class TestAccountMoveImport(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_open_wood = cls.env['res.partner'].create({
            'name': 'openWood',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'standard_price': 40.0,
        })

        cls.env['ir.sequence'].create({
            'name': 'TEST SEQUENCE',
            'code': 'purchase.order',
            'prefix': 'TESTPO',
            'padding': 5,
            'number_increment': 1,
            'company_id': cls.env.company.id,
        })

        cls.purchase_order = cls.env['purchase.order'].create({
            'partner_id': cls.partner_open_wood.id,
            'date_order': fields.Date.today(),
            'order_line': [Command.create({
                'product_id': cls.product.id,
                'name': cls.product.name,
                'product_qty': 1.0,
            })],
        })
        cls.purchase_order.button_confirm()

    def _create_bill_from_xml(self, xml_file_path):
        file_path = f"{self.test_module}/tests/test_files/{xml_file_path}"
        with file_open(file_path, 'rb') as file:
            xml_attachment = self.env['ir.attachment'].create({
                'mimetype': 'application/xml',
                'name': 'test_bill.xml',
                'raw': file.read(),
            })
        return self._import_attachment(xml_attachment)

    def _import_attachment(self, attachment, journal=None):
        journal = journal or self.company_data["default_journal_purchase"]
        return self.env['account.journal'] \
            .with_context(default_journal_id=journal.id) \
            ._create_document_from_attachment(attachment.id)

    def test_import_purchase_order_reference_from_provided_field(self):
        """
        This test will try to match a purchase order when the purchase reference is in the provided field
        """
        bill = self._create_bill_from_xml("ubl_bis3_PO.xml")
        self.assertEqual(bill.invoice_origin, self.purchase_order.name)
        # Checks if all lines referencing a PO reference the PO we created in setup.
        # The 'or [False]' makes sure that there's at least one line referencing a PO.
        self.assertTrue(all([line.purchase_order_id == self.purchase_order for line in bill.line_ids if line.purchase_order_id] or [False]))

    def test_import_purchase_order_reference_from_lines_description(self):
        """
        This test will try to match a purchase order when the purchase reference is not
        in the provided field but in the lines descriptions
        """
        bill = self._create_bill_from_xml("ubl_bis3_PO_description.xml")
        self.assertEqual(bill.invoice_origin, self.purchase_order.name)
        # Checks if all lines referencing a PO reference the PO we created in setup.
        # The 'or [False]' makes sure that there's at least one line referencing a PO.
        self.assertTrue(all([line.purchase_order_id == self.purchase_order for line in bill.line_ids if line.purchase_order_id] or [False]))

    def test_multiple_purchase_order_references(self):
        """
        This test checks that we find the purchase_order_id when giving multiple possible
        references in the 'invoice_origin' field
        """
        # Test with reference
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_origin': f'{self.purchase_order.name} TESTPO99932 TESTPO00001',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 40,
            })]
        })
        bill._link_bill_origin_to_purchase_orders()
        self.assertEqual(bill.invoice_origin, self.purchase_order.name)
        self.assertTrue(all(line.purchase_order_id == self.purchase_order for line in bill.line_ids if line.purchase_order_id))

        # Test without ref
        bill_2 = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_origin': 'TESTPO99932 TESTPO09876',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 40,
            })]
        })
        bill_2._link_bill_origin_to_purchase_orders()
        self.assertFalse(bill_2.invoice_origin)
        self.assertTrue(all(not line.purchase_order_id for line in bill_2.line_ids))

    def test_po_matching_no_partner_override(self):
        """
        When importing a bill, and it matches with a purchase order, the partner on
        the bill should be the same as the po partner
        """
        self.partner_open_wood.vat = 'BE0246697724'
        # First, should set the parent as no child exists
        bill = self._create_bill_from_xml('ubl_bis3_PO.xml')
        expected_parent = [{
            'invoice_origin': self.purchase_order.name,
            'partner_id': self.partner_open_wood.id,
        }]
        self.assertRecordValues(bill, expected_parent)
        bill.unlink()

        # Then, create a child of 'invoice' type -> still should set the parent
        child = self.env['res.partner'].create({
            'name': 'Test Child openwood',
            'type': 'invoice',
            'parent_id': self.partner_open_wood.id,
        })

        bill = self._create_bill_from_xml('ubl_bis3_PO.xml')
        self.assertRecordValues(bill, expected_parent)

        # Finally, create a PO with the child as partner -> should find the child
        po_child = self.env['purchase.order'].create({
            'partner_id': child.id,
            'date_order': fields.Date.today(),
            'order_line': [Command.create({
                'product_id': self.product.id,
                'name': self.product.name,
                'product_qty': 1.0,
                'tax_ids': [Command.clear()],
            })],
        })
        po_child.button_confirm()
        bill_child = self._create_bill_from_xml('ubl_bis3_PO.xml')
        self.assertRecordValues(bill_child, [{
            'invoice_origin': po_child.name,
            'partner_id': child.id,
        }])

    def _create_vehicles(self):
        self.ensure_installed('account_fleet')
        brand = self.env['fleet.vehicle.model.brand'].sudo().create({'name': 'Test Brand'})  # noqa: OLS03001
        model = self.env['fleet.vehicle.model'].sudo().create({'name': 'Test Model', 'brand_id': brand.id})  # noqa: OLS03001
        return self.env['fleet.vehicle'].sudo().create([  # noqa: OLS03001
            {'model_id': model.id, 'license_plate': '1-ABC-123'},
            {'model_id': model.id, 'vin_sn': 'ABCDEF012346GHJKL'},
        ])

    def test_po_total_match_keeps_imported_vehicles(self):
        """
        When an imported bill fully matches a purchase order, its lines are replaced by
        the purchase order lines. The vehicles found in the XML must be kept on them.
        """
        car_1, car_2 = self._create_vehicles()
        product_lease, product_fuel = self.env['product.product'].create([
            {'name': 'Car Lease', 'default_code': 'CAR-LEASE', 'supplier_taxes_id': False},
            {'name': 'Car Fuel', 'default_code': 'CAR-FUEL', 'supplier_taxes_id': False},
        ])
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_open_wood.id,
            'partner_ref': 'VEHICLE-PO',
            'order_line': [
                Command.create({'product_id': product_lease.id, 'product_qty': 1.0, 'price_unit': 100.0, 'tax_ids': False}),
                Command.create({'product_id': product_fuel.id, 'product_qty': 1.0, 'price_unit': 200.0, 'tax_ids': False}),
            ],
        })
        purchase_order.button_confirm()

        bill = self._create_bill_from_xml('ubl_bis3_PO_vehicle.xml')
        self.assertRecordValues(bill.invoice_line_ids.filtered(lambda l: l.display_type == 'product'), [
            {'purchase_line_id': purchase_order.order_line[0].id, 'vehicle_id': car_1.id},
            {'purchase_line_id': purchase_order.order_line[1].id, 'vehicle_id': car_2.id},
        ])

    def test_po_total_match_keeps_single_vehicle(self):
        """
        When the bill lines replaced by the purchase order lines all share the same vehicle,
        it is set on all the purchase order lines, even if their products differ.
        """
        car = self._create_vehicles()[0]
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_origin': self.purchase_order.name,
            'partner_id': self.partner_open_wood.id,
            'invoice_line_ids': [Command.create({
                'name': 'Car rental',
                'quantity': 1,
                'price_unit': self.purchase_order.amount_untaxed,
                'tax_ids': self.purchase_order.order_line.tax_ids.ids,
                'vehicle_id': car.id,
            })],
        })
        bill._link_bill_origin_to_purchase_orders()
        self.assertRecordValues(bill.invoice_line_ids.filtered(lambda l: l.display_type == 'product'), [
            {'purchase_line_id': self.purchase_order.order_line.id, 'vehicle_id': car.id},
        ])
