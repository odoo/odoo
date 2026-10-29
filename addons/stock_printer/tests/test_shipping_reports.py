# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged

from odoo.addons.printer.tests.test_printer import make_image


class TestShippingReports(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report_labels = cls.env.ref('stock_printer.action_report_shipping_labels')
        cls.report_documents = cls.env.ref('stock_printer.action_report_shipping_documents')
        cls.printer_zpl, cls.printer_epos = cls.env['printer.printer'].create([
            {'name': "Packing station", 'address': '192.168.1.20', 'kind': 'zpl'},
            {'name': "Shipping desk", 'address': '192.168.1.21', 'kind': 'epos'},
        ])
        cls.picking_type = cls.env.ref('stock.picking_type_out')
        cls.picking = cls.env['stock.picking'].create({'picking_type_id': cls.picking_type.id})
        cls.other_picking = cls.env['stock.picking'].create({'picking_type_id': cls.picking_type.id})

    def attach(self, name, raw, picking=None):
        return self.env['ir.attachment'].create({
            'name': name,
            'raw': raw,
            'res_model': 'stock.picking',
            'res_id': (picking or self.picking).id,
        })

    def render_printer_documents(self, report, printers, pickings=None):
        return self.env['ir.actions.report']._render_printer_documents(
            report, printers, (pickings or self.picking).ids)

    def render_pdf(self, report, pickings=None):
        return self.env['ir.actions.report']._render_qweb_pdf(report, (pickings or self.picking).ids)

    def test_print_on_printers(self):
        self.attach('LabelShipping-fedex-1.zpl', b'^XA^FDfirst^FS^XZ')
        self.attach('LabelShipping-fedex-2.png', make_image(200, 300))
        self.attach('LabelShipping-fedex-3.ZPL', b'^XA^FDlast^FS^XZ')
        self.attach('LabelShipping-fedex-4.pdf', b'%PDF-1.4')
        self.attach('ShippingDoc-fedex-1.zpl', b'^XA^FDdoc^FS^XZ')
        self.attach('Invoice.zpl', b'^XA^FDinvoice^FS^XZ')
        self.attach('LabelShipping-fedex-other.zpl', b'^XA^FDother^FS^XZ', picking=self.other_picking)

        documents = self.render_printer_documents(self.report_labels, self.printer_zpl | self.printer_epos)
        # The ZPL printers get the ZPL labels and the ePOS printers the image
        # ones, the most recent first.
        self.assertEqual(documents['zpl'], ['^XA^FDlast^FS^XZ', '^XA^FDfirst^FS^XZ'])
        [image] = documents['epos']
        self.assertEqual((image['width'], image['height']), (576, 864))

        self.assertEqual(
            self.render_printer_documents(self.report_documents, self.printer_zpl),
            {'zpl': ['^XA^FDdoc^FS^XZ']},
        )
        self.assertEqual(
            self.render_printer_documents(self.report_documents, self.printer_zpl, self.picking | self.other_picking),
            {'zpl': ['^XA^FDdoc^FS^XZ']},
        )
        self.assertEqual(
            self.render_printer_documents(self.report_labels, self.printer_zpl, self.picking | self.other_picking),
            {'zpl': ['^XA^FDother^FS^XZ', '^XA^FDlast^FS^XZ', '^XA^FDfirst^FS^XZ']},
        )

    def test_download(self):
        with self.assertRaisesRegex(UserError, "There is no Shipping Labels to print in the chatter"):
            self.render_pdf(self.report_labels)

        self.attach('LabelShipping-ups-1.pdf', b'%PDF-1.4 first')
        self.attach('ShippingDoc-ups-1.pdf', b'%PDF-1.4 doc')
        self.assertEqual(self.render_pdf(self.report_labels), (b'%PDF-1.4 first', 'pdf'))
        self.assertEqual(self.render_pdf(self.report_documents), (b'%PDF-1.4 doc', 'pdf'))

        # The most recent label is not a PDF: it is meant for printers.
        self.attach('LabelShipping-ups-2.zpl', b'^XA^XZ')
        with self.assertRaisesRegex(UserError, "has no printer configured"):
            self.render_pdf(self.report_labels)
        self.report_labels.printer_ids = self.printer_zpl
        with self.assertRaisesRegex(UserError, "Configure the carrier to produce PDF"):
            self.render_pdf(self.report_labels)

        self.attach('LabelShipping-ups-3.pdf', b'%PDF-1.4 last')
        self.assertEqual(self.render_pdf(self.report_labels), (b'%PDF-1.4 last', 'pdf'))

    def test_download_through_report_action(self):
        """ The download route serves the attachment. """
        self.attach('LabelShipping-ups-1.pdf', b'%PDF-1.4 label')
        content, report_type = self.env['ir.actions.report']._render(self.report_labels.report_name, self.picking.ids)
        self.assertEqual((content, report_type), (b'%PDF-1.4 label', 'pdf'))

    def test_auto_print(self):
        def autoprint_report_names():
            return [action['report_name'] for action in self.picking._get_autoprint_report_actions()]

        self.picking_type.write({
            'auto_print_delivery_slip': False,
            'auto_print_carrier_labels': True,
            'auto_print_export_documents': True,
        })
        # Without printer on the report, there is nothing to print.
        self.assertEqual(autoprint_report_names(), [])

        self.report_labels.printer_ids = self.printer_zpl
        self.assertEqual(autoprint_report_names(), ['stock_printer.report_shipping_labels'])
        [action] = self.picking._get_autoprint_report_actions()
        self.assertEqual(action['printer_ids'], self.printer_zpl.ids)
        self.assertEqual(action['context']['active_ids'], self.picking.ids)

        self.report_documents.printer_ids = self.printer_epos
        self.assertEqual(
            autoprint_report_names(),
            ['stock_printer.report_shipping_labels', 'stock_printer.report_shipping_documents'],
        )
        self.picking_type.auto_print_carrier_labels = False
        self.assertEqual(autoprint_report_names(), ['stock_printer.report_shipping_documents'])

    def test_report_form_link(self):
        action = self.picking_type.action_open_shipping_labels_report()
        self.assertEqual((action['res_model'], action['res_id']), ('ir.actions.report', self.report_labels.id))
        self.assertTrue(action['context']['printer_required'])
        action = self.picking_type.action_open_shipping_documents_report()
        self.assertEqual(action['res_id'], self.report_documents.id)


@tagged('post_install', '-at_install')
class TestShippingReportsDownload(HttpCase):

    def test_download(self):
        picking = self.env['stock.picking'].create({'picking_type_id': self.env.ref('stock.picking_type_out').id})
        report_name = self.env.ref('stock_printer.action_report_shipping_labels').report_name
        new_test_user(self.env, 'warehouse_worker', groups='stock.group_stock_user')
        self.authenticate('warehouse_worker', 'warehouse_worker')

        def download():
            return self.url_open('/report/download', data={
                'data': json.dumps([f'/report/pdf/{report_name}/{picking.id}', 'qweb-pdf']),
                'csrf_token': self.csrf_token(),
            })

        with self.assertLogs('odoo.addons.web.controllers.report', 'WARNING'):
            response = download()
        # the download helper of the web client shows the error to the user
        self.assertIn("There is no Shipping Labels to print", response.text)

        self.env['ir.attachment'].create({
            'name': 'LabelShipping-ups-1.pdf',
            'raw': b'%PDF-1.4 label',
            'res_model': 'stock.picking',
            'res_id': picking.id,
        })
        response = download()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'%PDF-1.4 label')
        self.assertIn('Shipping%20Labels.pdf', response.headers['Content-Disposition'])


class TestPrinterAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock_user = new_test_user(cls.env, 'stock_user', groups='stock.group_stock_user')
        cls.stock_manager = new_test_user(cls.env, 'stock_manager', groups='stock.group_stock_manager')
        cls.employee = new_test_user(cls.env, 'employee', groups='base.group_user')
        cls.report_labels = cls.env.ref('stock_printer.action_report_shipping_labels')

    def test_printer_access(self):
        Printer = self.env['printer.printer'].with_user(self.employee)
        printer = Printer.create({'name': "Zebra", 'address': '10.0.0.3', 'report_ids': [Command.link(self.report_labels.id)]})
        printer.write({'kind': 'epos', 'report_ids': [Command.clear()]})
        with self.assertRaises(AccessError):
            printer.unlink()
        with self.assertRaises(AccessError):
            printer.with_user(self.stock_user).unlink()
        printer.with_user(self.stock_manager).unlink()

    def test_menus(self):
        def visible_menus(user):
            menus = self.env['ir.ui.menu'].with_user(user)._visible_menu_ids()
            return {
                xml_id
                for xml_id in (
                    'stock.menu_stock_config_settings',
                    'stock.menu_product_in_config_stock',
                    'stock.menu_warehouse_config',
                    'stock_printer.menu_stock_config_reporting',
                    'stock_printer.menu_printer_printer',
                    'stock_printer.menu_reset_linked_printers',
                )
                if self.env.ref(xml_id).id in menus
            }

        self.assertEqual(visible_menus(self.stock_user), {
            'stock.menu_stock_config_settings',
            'stock_printer.menu_stock_config_reporting',
            'stock_printer.menu_reset_linked_printers',
        })
        self.assertEqual(visible_menus(self.stock_manager), {
            'stock.menu_stock_config_settings',
            'stock.menu_product_in_config_stock',
            'stock.menu_warehouse_config',
            'stock_printer.menu_stock_config_reporting',
            'stock_printer.menu_printer_printer',
            'stock_printer.menu_reset_linked_printers',
        })
