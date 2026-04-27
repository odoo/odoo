from dateutil.relativedelta import relativedelta

import base64

from odoo import Command
from odoo.addons.l10n_mx_edi.tests.common import EXTERNAL_MODE
from odoo.tests import tagged
from odoo.tools import misc
from .common import TestMXEdiStockCommon


@tagged('post_install_l10n', 'post_install', '-at_install', *(['-standard', 'external'] if EXTERNAL_MODE else []))
class TestCFDIPickingXml(TestMXEdiStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vehicle_pedro.write({
            'environment_insurer': 'DEMO INSURER',
            'environment_insurance_policy': 'DEMO INSURER POLICY',
        })

    def test_delivery_guide_outgoing(self):
        with self.mx_external_setup(self.frozen_today):
            warehouse = self._create_warehouse()
            picking = self._create_picking(warehouse)
            with self.with_mocked_pac_sign_success():
                picking.l10n_mx_edi_cfdi_try_send()

            self._assert_picking_cfdi(picking, 'test_delivery_guide_outgoing')

        self._assert_picking_cfdi(picking, 'test_delivery_guide_outgoing')

    def test_delivery_guide_incoming(self):
        with self.mx_external_setup(self.frozen_today):
            warehouse = self._create_warehouse()
            picking = self._create_picking(warehouse, outgoing=False)
            with self.with_mocked_pac_sign_success():
                picking.l10n_mx_edi_cfdi_try_send()

            self._assert_picking_cfdi(picking, 'test_delivery_guide_incoming')

    def test_delivery_guide_comex_outgoing(self):
        self.product.l10n_mx_edi_material_type = '05'
        self.product.l10n_mx_edi_material_description = 'Test material description'

        with self.mx_external_setup(self.frozen_today):
            warehouse = self._create_warehouse()
            picking = self._create_picking(
                warehouse,
                picking_vals={
                    'partner_id': self.partner_us.id,
                    'l10n_mx_edi_customs_document_type_id': self.env.ref('l10n_mx_edi_stock.l10n_mx_edi_customs_document_type_02').id,
                    'l10n_mx_edi_customs_doc_identification': '0123456789',
                    'l10n_mx_edi_customs_regime_ids': [Command.set([
                        self.custom_regime_imd.id,
                        self.custom_regime_exd.id,
                    ])],
                },
            )

            with self.with_mocked_pac_sign_success():
                picking.l10n_mx_edi_cfdi_try_send()

            self._assert_picking_cfdi(picking, 'test_delivery_guide_comex_outgoing')

    def test_delivery_guide_comex_incoming(self):
        self.product.l10n_mx_edi_material_type = '01'

        with self.mx_external_setup(self.frozen_today):
            warehouse = self._create_warehouse()
            picking = self._create_picking(
                warehouse,
                outgoing=False,
                picking_vals={
                    'partner_id': self.partner_us.id,
                    'l10n_mx_edi_customs_document_type_id': self.env.ref('l10n_mx_edi_stock.l10n_mx_edi_customs_document_type_01').id,
                    'l10n_mx_edi_importer_id': self.partner_mx.id,
                    'l10n_mx_edi_customs_regime_ids': [Command.set([
                        self.custom_regime_imd.id,
                        self.custom_regime_exd.id,
                    ])],
                    'l10n_mx_edi_pedimento_number': "15  48  3009  0001234",
                },
            )

            with self.with_mocked_pac_sign_success():
                picking.l10n_mx_edi_cfdi_try_send()

            self._assert_picking_cfdi(picking, 'test_delivery_guide_comex_incoming')

    def test_delivery_guide_company_branch(self):
        with self.mx_external_setup(self.frozen_today - relativedelta(hours=1)):
            self.env.company.write({
                'child_ids': [Command.create({
                    'name': "Branch A",
                    'street': 'Campobasso Norte 3260 - 9000',
                    'street2': self.env.company.street2,
                    'zip': self.env.company.zip,
                    'city': self.env.company.city,
                    'country_id': self.env.company.country_id.id,
                    'state_id': self.env.company.state_id.id,
                })],
            })
            self.cr.precommit.run()  # load the CoA
            branch = self.env.company.child_ids
            key = self.env['certificate.key'].create({
                'content': base64.encodebytes(misc.file_open('l10n_mx_edi/demo/pac_credentials/certificate.key', 'rb').read()),
                'password': '12345678a',
                'company_id': branch.id,
            })
            certificate = self.env['certificate.certificate'].create({
                'content': base64.encodebytes(misc.file_open('l10n_mx_edi/demo/pac_credentials/certificate.cer', 'rb').read()),
                'private_key_id': key.id,
                'company_id': branch.id,
            })
            branch.l10n_mx_edi_certificate_ids = certificate
            branch.partner_id.write({
                'street_name': self.env.company.partner_id.street_name,
                'street_number': self.env.company.partner_id.street_number,
                'street_number2': self.env.company.partner_id.street_number2,
                'city_id': self.env.company.partner_id.city_id.id,
            })
            self.product.company_id = branch
            warehouse = self._create_warehouse(company_id=branch.id, partner_id=branch.partner_id.id)
            picking = self._create_picking(warehouse)

            with self.with_mocked_pac_sign_success():
                picking.l10n_mx_edi_cfdi_try_send()
            self._assert_picking_cfdi(picking, 'test_delivery_guide_company_branch')

    def test_delivery_guide_hazardous_product_outgoing(self):
        '''Test the delivery guide of an (1) hazardous product'''
        self.product.write({
            'unspsc_code_id': self.env.ref('product_unspsc.unspsc_code_12352120').id,
            'l10n_mx_edi_hazardous_material_code_id': self.env.ref('l10n_mx_edi_stock.hazardous_material_413'),
            'l10n_mx_edi_hazard_package_type': '1H1',
        })
        with self.mx_external_setup(self.frozen_today):
            warehouse = self._create_warehouse()
            picking = self._create_picking(warehouse)

            with self.with_mocked_pac_sign_success():
                picking.l10n_mx_edi_cfdi_try_send()

            self._assert_picking_cfdi(picking, 'test_delivery_guide_hazardous_product_outgoing')

    def test_delivery_guide_maybe_hazardous_product_outgoing_0(self):
        '''Test the delivery guide of a maybe (0,1) hazardous product
           Instance not hazardous
        '''
        self.product.write({
            'unspsc_code_id': self.env.ref('product_unspsc.unspsc_code_12352106').id,
        })
        with self.mx_external_setup(self.frozen_today):
            warehouse = self._create_warehouse()
            picking = self._create_picking(warehouse)

            with self.with_mocked_pac_sign_success():
                picking.l10n_mx_edi_cfdi_try_send()

            self._assert_picking_cfdi(picking, 'test_delivery_guide_maybe_hazardous_product_outgoing_0')

    def test_delivery_guide_maybe_hazardous_product_outgoing_1(self):
        '''Test the delivery guide of a maybe (0,1) hazardous product
           Instance hazardous
        '''
        self.product.write({
            'unspsc_code_id': self.env.ref('product_unspsc.unspsc_code_12352106').id,
            'l10n_mx_edi_hazardous_material_code_id': self.env.ref('l10n_mx_edi_stock.hazardous_material_413'),
            'l10n_mx_edi_hazard_package_type': '1H1',
        })
        with self.mx_external_setup(self.frozen_today):
            warehouse = self._create_warehouse()
            picking = self._create_picking(warehouse)

            with self.with_mocked_pac_sign_success():
                picking.l10n_mx_edi_cfdi_try_send()

            self._assert_picking_cfdi(picking, 'test_delivery_guide_maybe_hazardous_product_outgoing_1')

    def test_delivery_guide_outgoing_delivery_address(self):
        '''Test the delivery guide with a delivery address different than main address'''
        delivery_address = self.env['res.partner'].create({
            'parent_id': self.partner_mx.id,
            'type': 'delivery',
            'street': 'XYZ 1234 - 5678',
            'city_id': self.env.ref('l10n_mx_edi_extended.res_city_mx_mex_002').id,
            'state_id': self.env.ref('base.state_mx_mex').id,
            'zip': '55870',
            'country_id': self.env.ref('base.mx').id,
        })
        with self.mx_external_setup(self.frozen_today):
            warehouse = self._create_warehouse()
            picking = self._create_picking(
                warehouse,
                picking_vals={'partner_id': delivery_address.id}
            )

            with self.with_mocked_pac_sign_success():
                picking.l10n_mx_edi_cfdi_try_send()

            self._assert_picking_cfdi(picking, 'test_delivery_guide_outgoing_delivery_address')
