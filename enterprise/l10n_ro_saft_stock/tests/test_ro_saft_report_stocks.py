from datetime import datetime
from freezegun import freeze_time
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.addons.l10n_ro_saft.tests.test_ro_saft_report_assets import TestRoSaftReportAssets


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestRoSaftReportStocks(TestRoSaftReportAssets):
    """ Test the generation of the SAF-T Stocks Declaration export for Romania."""

    @classmethod
    @TestAccountReportsCommon.setup_country('ro')
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.groups_id += cls.env.ref('stock_account.group_stock_accounting_automatic')

        company = cls.company_data['company']
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=company.ids))

        wh = cls.env.user._get_default_warehouse_id()
        loc = wh.lot_stock_id
        loc_customers = cls.env.ref('stock.stock_location_customers')
        loc_suppliers = cls.env.ref('stock.stock_location_suppliers')
        pt_in = wh.in_type_id
        pt_out = wh.out_type_id
        pt_int = wh.int_type_id
        pt_int.active = True
        pt_in.sequence = 10
        pt_out.sequence = 30
        pt_int.sequence = 80

        loc_a, loc_b, loc_c = cls.env['stock.location'].create([
            {
                'name': 'Location A',
                'usage': 'internal',
                'company_id': company.id,
                'location_id': loc.id,
            },
            {
                'name': 'Location B',
                'usage': 'internal',
                'company_id': company.id,
                'location_id': loc.id,
            },
            {
                'name': 'Location C',
                'usage': 'internal',
                'company_id': company.id,
                'location_id': loc.id,
            },
        ])

        pc1, pc2, pc3 = cls.env['product.category'].create([
            {
                'name': 'Category 1',
                'property_cost_method': 'standard',
            },
            {
                'name': 'Category 2',
                'property_cost_method': 'fifo',
            },
            {
                'name': 'Category 3',
                'property_cost_method': 'average',
            },
        ])

        p1, p2, p3, p4, p5, p6 = cls.env['product.product'].create([
            {
                'name': 'Product 1',
                'type': 'consu',
                'is_storable': True,
                'standard_price': 10,
                'categ_id': pc1.id,
                'default_code': 'RO-P1',
            },
            {
                'name': 'Product 2',
                'type': 'consu',
                'is_storable': True,
                'standard_price': 20,
                'categ_id': pc1.id,
                'default_code': 'RO-P2',
            },
            {
                'name': 'Product 3',
                'type': 'consu',
                'is_storable': True,
                'standard_price': 30,
                'categ_id': pc1.id,
                'default_code': 'RO-P3',
            },
            {
                'name': 'Product 4',
                'type': 'consu',
                'is_storable': True,
                'standard_price': 10,
                'categ_id': pc1.id,
                'default_code': 'RO-P4',
            },
            {
                'name': 'Product 5',
                'type': 'consu',
                'is_storable': True,
                'standard_price': 10,
                'categ_id': pc2.id,
                'default_code': 'RO-P5',
            },
            {
                'name': 'Product 6',
                'type': 'consu',
                'is_storable': True,
                'standard_price': 10,
                'categ_id': pc3.id,
                'default_code': 'RO-P6',
            },
        ])
        if 'intrastat_code_id' in cls.env['product.product']._fields:
            (p1 | p2 | p3 | p4 | p5 | p6).intrastat_code_id = cls.env['account.intrastat.code'].sudo().create({
                'code': '0',
                'type': 'commodity',
            })

        feb_date = datetime(2025, 2, 10, 12, 0, 0)
        with freeze_time(feb_date), patch.object(cls.env.cr, 'now', lambda: feb_date):
            cls.env['stock.quant'].create([
                {
                    'product_id': p1.id,
                    'location_id': loc_a.id,
                    'inventory_quantity': 100,
                },
                {
                    'product_id': p1.id,
                    'location_id': loc_b.id,
                    'inventory_quantity': 150,
                },
                {
                    'product_id': p2.id,
                    'location_id': loc_a.id,
                    'inventory_quantity': 60,
                },
            ]).action_apply_inventory()

            cls.env['stock.picking'].with_context(demo_mode=True).create([
                {
                    'name': 'Picking 1',
                    'company_id': company.id,
                    'location_id': loc_suppliers.id,
                    'location_dest_id': loc_a.id,
                    'picking_type_id': pt_in.id,
                    'move_ids': [
                        Command.create({
                            'name': 'Stock move 1.1',
                            'product_id': p4.id,
                            'company_id': company.id,
                            'product_uom_qty': 10,
                            'price_unit': 10,
                            'sequence': 10,
                        }),
                        Command.create({
                            'name': 'Stock move 1.2',
                            'product_id': p5.id,
                            'company_id': company.id,
                            'product_uom_qty': 10,
                            'price_unit': 10,
                            'sequence': 20,
                        }),
                        Command.create({
                            'name': 'Stock move 1.3',
                            'product_id': p6.id,
                            'company_id': company.id,
                            'product_uom_qty': 10,
                            'price_unit': 10,
                            'sequence': 30,
                        }),
                    ],
                },
                {
                    'name': 'Picking 2',
                    'company_id': company.id,
                    'location_id': loc_a.id,
                    'location_dest_id': loc_customers.id,
                    'picking_type_id': pt_out.id,
                    'partner_id': cls.partner_a.id,
                    'move_ids': [
                        Command.create({
                            'name': 'Stock move 2.1',
                            'product_id': p1.id,
                            'company_id': company.id,
                            'product_uom_qty': 50,
                            'sequence': 40,
                        }),
                        Command.create({
                            'name': 'Stock move 2.2',
                            'product_id': p2.id,
                            'company_id': company.id,
                            'product_uom_qty': 20,
                            'sequence': 50,
                        }),
                    ],
                },
                {
                    'name': 'Picking 3',
                    'company_id': company.id,
                    'location_id': loc_suppliers.id,
                    'location_dest_id': loc_b.id,
                    'picking_type_id': pt_in.id,
                    'partner_id': cls.partner_b.id,
                    'move_ids': [
                        Command.create({
                            'name': 'Stock move 3.1',
                            'product_id': p3.id,
                            'company_id': company.id,
                            'product_uom_qty': 50,
                            'sequence': 60,
                        }),
                    ],
                },
                {
                    'name': 'Picking 4',
                    'company_id': company.id,
                    'location_id': loc_suppliers.id,
                    'location_dest_id': loc_c.id,
                    'picking_type_id': pt_in.id,
                    'partner_id': cls.partner_b.id,
                    'move_ids': [
                        Command.create({
                            'name': 'Stock move 4.1',
                            'product_id': p2.id,
                            'company_id': company.id,
                            'product_uom_qty': 20,
                            'sequence': 70,
                        }),
                    ],
                },
                {
                    'name': 'Picking 5',
                    'company_id': company.id,
                    'location_id': loc_a.id,
                    'location_dest_id': loc_b.id,
                    'picking_type_id': pt_int.id,
                    'move_ids': [
                        Command.create({
                            'name': 'Stock move 5.1',
                            'product_id': p2.id,
                            'company_id': company.id,
                            'product_uom_qty': 10,
                            'sequence': 80,
                        }),
                    ],
                },
                {
                    'name': 'Picking 6',
                    'company_id': company.id,
                    'location_id': loc_a.id,
                    'location_dest_id': loc_c.id,
                    'picking_type_id': pt_int.id,
                    'move_ids': [
                        Command.create({
                            'name': 'Stock move 6.1',
                            'product_id': p2.id,
                            'company_id': company.id,
                            'product_uom_qty': 10,
                            'sequence': 90,
                        }),
                    ],
                },
            ]).button_validate()

        mar_date = datetime(2025, 3, 9, 12, 0, 0)
        with freeze_time(mar_date), patch.object(cls.env.cr, 'now', lambda: mar_date):
            cls.env['stock.quant'].create([
                {
                    'product_id': p2.id,
                    'location_id': loc_c.id,
                    'inventory_quantity': 20,
                },
                {
                    'product_id': p1.id,
                    'location_id': loc_c.id,
                    'inventory_quantity': 17,
                    'owner_id': cls.partner_b.id,
                },
            ]).action_apply_inventory()

            cls.env['stock.picking'].with_context(demo_mode=True).create([
                {
                    'name': 'Picking 7',
                    'company_id': company.id,
                    'location_id': loc_b.id,
                    'location_dest_id': loc_customers.id,
                    'picking_type_id': pt_out.id,
                    'partner_id': cls.partner_a.id,
                    'move_ids': [
                        Command.create({
                            'name': 'Stock move 7.1',
                            'product_id': p1.id,
                            'company_id': company.id,
                            'product_uom_qty': 47,
                            'sequence': 100,
                        }),
                    ],
                },
                {
                    'name': 'Picking 8',
                    'company_id': company.id,
                    'location_id': loc_suppliers.id,
                    'location_dest_id': loc_a.id,
                    'picking_type_id': pt_in.id,
                    'partner_id': cls.partner_b.id,
                    'move_ids': [
                        Command.create({
                            'name': 'Stock move 8.1',
                            'product_id': p2.id,
                            'company_id': company.id,
                            'product_uom_qty': 50,
                            'sequence': 110,
                        }),
                        Command.create({
                            'name': 'Stock move 8.2',
                            'product_id': p3.id,
                            'company_id': company.id,
                            'product_uom_qty': 100,
                            'sequence': 120,
                        }),
                    ],
                },
                {
                    'name': 'Picking 9',
                    'company_id': company.id,
                    'location_id': loc_a.id,
                    'location_dest_id': loc_b.id,
                    'picking_type_id': pt_int.id,
                    'move_ids': [
                        Command.create({
                            'name': 'Stock move 9.1',
                            'product_id': p3.id,
                            'company_id': company.id,
                            'product_uom_qty': 10,
                            'sequence': 130,
                        }),
                    ],
                },
                {
                    'name': 'Picking 10',
                    'company_id': company.id,
                    'location_id': loc_a.id,
                    'location_dest_id': loc_c.id,
                    'picking_type_id': pt_int.id,
                    'move_ids': [
                        Command.create({
                            'name': 'Stock move 10.1',
                            'product_id': p3.id,
                            'company_id': company.id,
                            'product_uom_qty': 40,
                            'sequence': 140,
                        }),
                    ],
                },
                {
                    'name': 'Picking 11',
                    'company_id': company.id,
                    'location_id': loc_suppliers.id,
                    'location_dest_id': loc_a.id,
                    'picking_type_id': pt_in.id,
                    'move_ids': [
                        Command.create({
                            'name': 'Stock move 11.1',
                            'product_id': p4.id,
                            'company_id': company.id,
                            'product_uom_qty': 10,
                            'price_unit': 100,
                            'sequence': 150,
                        }),
                        Command.create({
                            'name': 'Stock move 11.2',
                            'product_id': p5.id,
                            'company_id': company.id,
                            'product_uom_qty': 10,
                            'price_unit': 100,
                            'sequence': 160,
                        }),
                        Command.create({
                            'name': 'Stock move 11.3',
                            'product_id': p6.id,
                            'company_id': company.id,
                            'product_uom_qty': 10,
                            'price_unit': 100,
                            'sequence': 170,
                        }),
                    ],
                },
                {
                    'name': 'Picking 12',
                    'company_id': company.id,
                    'location_id': loc_a.id,
                    'picking_type_id': pt_out.id,
                    'move_ids': [
                        Command.create({
                            'name': 'Stock move 12.1',
                            'product_id': p4.id,
                            'company_id': company.id,
                            'product_uom_qty': 1,
                            'sequence': 180,
                        }),
                        Command.create({
                            'name': 'Stock move 12.2',
                            'product_id': p5.id,
                            'company_id': company.id,
                            'product_uom_qty': 1,
                            'sequence': 190,
                        }),
                        Command.create({
                            'name': 'Stock move 12.3',
                            'product_id': p6.id,
                            'company_id': company.id,
                            'product_uom_qty': 1,
                            'sequence': 200,
                        }),
                    ],
                },
            ]).button_validate()

        may_date = datetime(2025, 5, 9, 12, 0, 0)
        with freeze_time(may_date), patch.object(cls.env.cr, 'now', lambda: may_date):
            cls.env['stock.picking'].with_context(demo_mode=True).create([
                {
                    'name': 'Picking 13',
                    'company_id': company.id,
                    'location_id': loc_a.id,
                    'location_dest_id': loc_customers.id,
                    'picking_type_id': pt_out.id,
                    'partner_id': cls.partner_a.id,
                    'move_ids': [
                        Command.create({
                            'name': 'Stock move 13.1',
                            'product_id': p1.id,
                            'company_id': company.id,
                            'product_uom_qty': 50,
                            'sequence': 81,
                        }),
                    ],
                },
            ]).button_validate()

    @freeze_time('2025-03-10')
    def test_l10n_ro_saft_report_stocks_1(self):
        generated_report = self.report_handler.l10n_ro_export_saft_to_xml_stocks(self._generate_options(date_from='2025-02-01', date_to='2025-02-28'))
        self._report_compare_with_test_file(
            generated_report,
            'saft_report_stocks_1.xml'
        )

    @freeze_time('2025-04-10')
    def test_l10n_ro_saft_report_stocks_2(self):
        generated_report = self.report_handler.l10n_ro_export_saft_to_xml_stocks(self._generate_options(date_from='2025-03-01', date_to='2025-03-31'))
        self._report_compare_with_test_file(
            generated_report,
            'saft_report_stocks_2.xml'
        )

    @freeze_time('2025-05-10')
    def test_l10n_ro_saft_report_stocks_3(self):
        generated_report = self.report_handler.l10n_ro_export_saft_to_xml_stocks(self._generate_options(date_from='2025-03-01', date_to='2025-03-31'))
        self._report_compare_with_test_file(
            generated_report,
            'saft_report_stocks_3.xml'
        )
