from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import freeze_time, new_test_user, tagged

from odoo.addons.l10n_ar.tests.common import TestArCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
@freeze_time('2026-11-05 12:00:00')
class TestArCot(TestArCommon):

    _test_user_groups = (
        'stock.group_stock_user',  # subject: transfers and their COT
        'stock.group_stock_manager',  # setup: picking type of the branch
        'base.group_system',  # setup: ARBA credentials and branch companies
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_ri.l10n_ar_arba_cot_environment = 'demo'
        cls.env.ref('uom.product_uom_unit').l10n_ar_arba_unit_code = '3'
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'default_code': 'PROD-1',
            'l10n_ar_arba_code': '847150',
        })
        cls.carrier = cls.env['res.partner'].create({
            'name': 'Carrier',
            'vat': '20222222223',
            'l10n_ar_afip_responsibility_type_id': cls.env.ref('l10n_ar.res_RM').id,
        })
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_ri.id)], limit=1)
        cls.picking_type = cls.env['stock.picking.type'].create({
            'name': 'Remito Outgoing',
            'code': 'outgoing',
            'company_id': cls.company_ri.id,
            'sequence_code': 'OUT',
            'warehouse_id': cls.warehouse.id,
            'l10n_ar_document_type_id': cls.env.ref('l10n_ar.dc_r_r').id,
        })

    def test_cot_generation_demo(self):
        self.product.write({'name': 'Ñandú Café', 'default_code': 'PROD-1€'})
        self.res_partner_adhoc.write({'name': 'ADHOC| SA', 'street': 'Ovidio Lagos 41 bis€'})
        picking = self.env['stock.picking'].create({
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'picking_type_id': self.picking_type.id,
            'partner_id': self.res_partner_adhoc.id,
            'move_ids': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            })],
        })
        picking.action_confirm()
        picking.button_validate()
        picking.l10n_ar_action_create_delivery_guide()
        picking.write({
            'l10n_ar_cot_departure_date': '2026-11-06 10:00:00',
            'l10n_ar_cot_license_plate': 'AB123CD',
            'l10n_ar_cot_carrier_id': self.carrier.id,
            'l10n_ar_cot_amount': 1234.5,
        })
        picking.l10n_ar_action_generate_cot()

        self.assertEqual(picking.l10n_ar_cot_number, f'{picking.id:014d}')
        self.assertFalse(picking.l10n_ar_cot_error)
        txt = self.env['ir.attachment'].search([
            ('res_model', '=', 'stock.picking'),
            ('res_id', '=', picking.id),
            ('name', '=', 'TB_30111111118_000000_20261105_000001.txt'),
        ])
        self.assertEqual(txt.raw.decode('ISO-8859-1').splitlines(keepends=True), [
            '01|30111111118\n',
            (
                '02|20261105|0910000100000001|20261106|0700|E|0|||30714295698|ADHOC SA|0'
                '|Ovidio Lagos 41 bis?||S/N||||2000|Rosario|S||SI|30111111118|(AR) Responsable Inscripto (Unit Tests)|1'
                '|Calle Falsa 123||S/N||||2000|Rosario|S|20222222223|||||AB123CD||0|123450\n'
            ),
            '03|847150|3|500|PROD-1?|Ñandú Café|Units|500\n',
            '04|1\n',
        ])
        with self.assertRaisesRegex(UserError, "A COT can only be generated once"):
            picking.l10n_ar_action_generate_cot()

    def test_cot_missing_configuration(self):
        self.product.l10n_ar_arba_code = False
        picking = self.env['stock.picking'].create({
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'picking_type_id': self.picking_type.id,
            'partner_id': self.res_partner_adhoc.id,
            'move_ids': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            })],
        })
        picking.action_confirm()
        picking.button_validate()
        picking.l10n_ar_action_create_delivery_guide()
        picking.l10n_ar_cot_carrier_id = self.carrier

        self.company_ri.l10n_ar_arba_cot_environment = False
        self.assertFalse(picking.l10n_ar_is_cot_enabled)
        with self.assertRaisesRegex(UserError, "Select an ARBA COT Environment"):
            picking.l10n_ar_action_generate_cot()

        self.company_ri.l10n_ar_arba_cot_environment = 'demo'
        with self.assertRaisesRegex(
            UserError,
            r"- The Vehicle License Plate is missing\.\n"
            r"- The Net Amount of the Goods must be greater than 0\.\n"
            r"- Products without ARBA Code: \[PROD-1\] Test Product$",
        ):
            picking.l10n_ar_action_generate_cot()

        picking.l10n_ar_cot_is_non_finished_product = True
        with self.assertRaisesRegex(
            UserError,
            r":\n- The Vehicle License Plate is missing\.\n"
            r"- Products without ARBA Code: \[PROD-1\] Test Product$",
        ):
            picking.l10n_ar_action_generate_cot()

    def test_cot_error_response(self):
        self.company_ri.write({
            'l10n_ar_arba_cit': 'Password123',
            'l10n_ar_arba_cot_environment': 'testing',
        })
        picking = self.env['stock.picking'].create({
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'picking_type_id': self.picking_type.id,
            'partner_id': self.res_partner_adhoc.id,
            'move_ids': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            })],
        })
        picking.action_confirm()
        picking.button_validate()
        picking.l10n_ar_action_create_delivery_guide()
        picking.write({
            'l10n_ar_cot_departure_date': '2026-11-06 10:00:00',
            'l10n_ar_cot_license_plate': 'AB123CD',
            'l10n_ar_cot_carrier_id': self.carrier.id,
            'l10n_ar_cot_amount': 1234.5,
        })
        response_content = """<?xml version="1.0" encoding="ISO-8859-1" ?>
            <TBCOMPROBANTE>
                <cuitEmpresa>30111111118</cuitEmpresa>
                <validacionesRemitos class="list">
                    <remito>
                        <numeroUnico>0910000100000001</numeroUnico>
                        <procesado>NO</procesado>
                        <errores class="list">
                            <error>
                                <codigo>21</codigo>
                                <descripcion>El campo CODIGO_UNICO es inválido o inexistente.</descripcion>
                            </error>
                        </errores>
                    </remito>
                </validacionesRemitos>
            </TBCOMPROBANTE>""".encode('ISO-8859-1')

        with patch('odoo.addons.l10n_ar_stock.models.stock_picking.requests.post') as mock_post:
            mock_post.return_value.content = response_content
            picking.l10n_ar_action_generate_cot()

        self.assertEqual(mock_post.call_args.kwargs['data'], {'user': '30111111118', 'password': 'Password123'})
        self.assertFalse(picking.l10n_ar_cot_number)
        self.assertEqual(picking.l10n_ar_cot_error, '[21] El campo CODIGO_UNICO es inválido o inexistente.')

        with patch('odoo.addons.l10n_ar_stock.models.stock_picking.requests.post') as mock_post:
            mock_post.return_value.status_code = 500
            mock_post.return_value.content = b"""<TBError>
                <tipoError>DATO</tipoError>
                <codigoError>02</codigoError>
                <mensajeError>El usuario ingresado y/o la contrasena son invalidos.</mensajeError>
            </TBError>"""
            picking.l10n_ar_action_generate_cot()
        self.assertEqual(picking.l10n_ar_cot_error, '[02] El usuario ingresado y/o la contrasena son invalidos.')

        with patch('odoo.addons.l10n_ar_stock.models.stock_picking.requests.post') as mock_post:
            mock_post.return_value.status_code = 502
            mock_post.return_value.content = b'<html><body>Bad Gateway<br></body></html>'
            picking.l10n_ar_action_generate_cot()
        self.assertEqual(picking.l10n_ar_cot_error, "ARBA returned an invalid response.")

    def test_cot_generation_stock_user(self):
        self.company_ri.write({
            'l10n_ar_arba_cit': 'Password123',
            'l10n_ar_arba_cot_environment': 'testing',
        })
        stock_user = new_test_user(
            self.env,
            login='ar_stock_user',
            groups='stock.group_stock_user',
            company_id=self.company_ri.id,
            company_ids=self.company_ri.ids,
        )
        picking = self.env['stock.picking'].create({
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'picking_type_id': self.picking_type.id,
            'partner_id': self.res_partner_adhoc.id,
            'move_ids': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            })],
        })
        picking.action_confirm()
        picking.button_validate()
        picking.l10n_ar_action_create_delivery_guide()
        picking.write({
            'l10n_ar_cot_departure_date': '2026-11-06 10:00:00',
            'l10n_ar_cot_license_plate': 'AB123CD',
            'l10n_ar_cot_carrier_id': self.carrier.id,
            'l10n_ar_cot_amount': 1234.5,
        })

        with patch('odoo.addons.l10n_ar_stock.models.stock_picking.requests.post') as mock_post:
            mock_post.return_value.content = b"""<TBCOMPROBANTE>
                <cuitEmpresa>30111111118</cuitEmpresa>
                <validacionesRemitos class="list">
                    <remito>
                        <numeroUnico>0910000100000001</numeroUnico>
                        <procesado>SI</procesado>
                        <cot>12345678901234</cot>
                    </remito>
                </validacionesRemitos>
            </TBCOMPROBANTE>"""
            picking.with_user(stock_user).l10n_ar_action_generate_cot()

        self.assertEqual(mock_post.call_args.kwargs['data'], {'user': '30111111118', 'password': 'Password123'})
        self.assertEqual(picking.l10n_ar_cot_number, '12345678901234')
        self.assertFalse(picking.l10n_ar_cot_error)

    def test_cot_branch_credentials(self):
        self.company_ri.write({
            'l10n_ar_arba_cit': 'Password123',
            'l10n_ar_arba_cot_environment': 'testing',
        })
        branch = self.env['res.company'].create({
            'name': 'Branch',
            'parent_id': self.company_ri.id,
            'l10n_ar_arba_cit': 'BranchPassword',
            'l10n_ar_arba_cot_environment': 'testing',
        })
        sub_branch = self.env['res.company'].create({
            'name': 'Sub Branch',
            'parent_id': branch.id,
        })
        self.assertEqual(branch._l10n_ar_get_arba_cot_company(), self.company_ri)
        self.assertEqual(sub_branch._l10n_ar_get_arba_cot_company(), self.company_ri)

        branch.vat = self.company_ri.vat
        self.assertEqual(branch._l10n_ar_get_arba_cot_company(), branch)
        self.assertEqual(sub_branch._l10n_ar_get_arba_cot_company(), branch)

    def test_cot_branch_file_number(self):
        self.company_ri.l10n_ar_arba_cot_file_sequence_id = self.env['ir.sequence'].create({
            'name': 'COT File Sequence',
            'padding': 6,
            'number_next': 42,
        })
        branch = self.env['res.company'].create({
            'name': 'Branch',
            'parent_id': self.company_ri.id,
            'street': self.company_ri.street,
            'zip': self.company_ri.zip,
            'city': self.company_ri.city,
            'state_id': self.company_ri.state_id.id,
            'country_id': self.company_ri.country_id.id,
        })
        self.env.user.company_ids |= branch
        branch_warehouse = self.env['stock.warehouse'].search([('company_id', '=', branch.id)], limit=1)
        picking_type = self.picking_type.copy({
            'company_id': branch.id,
            'warehouse_id': branch_warehouse.id,
        })
        picking = self.env['stock.picking'].with_company(branch).create({
            'location_id': branch_warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'picking_type_id': picking_type.id,
            'partner_id': self.res_partner_adhoc.id,
            'move_ids': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
                'location_id': branch_warehouse.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            })],
        })
        picking.action_confirm()
        picking.button_validate()
        picking.l10n_ar_action_create_delivery_guide()
        picking.write({
            'l10n_ar_cot_departure_date': '2026-11-06 10:00:00',
            'l10n_ar_cot_license_plate': 'AB123CD',
            'l10n_ar_cot_carrier_id': self.carrier.id,
            'l10n_ar_cot_amount': 1234.5,
        })
        self.assertTrue(picking.l10n_ar_is_cot_enabled)
        picking.l10n_ar_action_generate_cot()

        self.assertTrue(self.env['ir.attachment'].search([
            ('res_model', '=', 'stock.picking'),
            ('res_id', '=', picking.id),
            ('name', '=', 'TB_30111111118_000000_20261105_000042.txt'),
        ]))
        self.assertFalse(branch.l10n_ar_arba_cot_file_sequence_id)
