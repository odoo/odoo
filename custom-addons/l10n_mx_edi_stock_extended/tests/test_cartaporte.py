from freezegun import freeze_time

from odoo.addons.l10n_mx_edi_stock_extended_30.tests.common import TestMXEdiStockCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCFDIPickingXml(TestMXEdiStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.partner_id.city_id = cls.env.ref('l10n_mx_edi_extended.res_city_mx_chh_032').id

        cls.partner_b.write({
            'street': 'Nevada Street',
            'city': 'Carson City',
            'country_id': cls.env.ref('base.us').id,
            'state_id': cls.env.ref('base.state_us_23').id,
            'zip': 39301,
            'vat': '123456789',
        })

        cls.vehicle_pedro.write({
            'environment_insurer': 'DEMO INSURER',
            'environment_insurance_policy': 'DEMO INSURER POLICY',
        })

    @freeze_time('2017-01-01')
    def test_delivery_guide_hazardous_product_outgoing(self):
        '''Test the delivery guide of an (1) hazardous product'''
        self.product.write({
            'unspsc_code_id': self.env.ref('product_unspsc.unspsc_code_12352120').id,
            'l10n_mx_edi_hazardous_material_code': '1052',
            'l10n_mx_edi_hazard_package_type': '1H1',
        })
        with self.mx_external_setup(self.frozen_today):
            warehouse = self._create_warehouse()
            picking = self._create_picking(warehouse)

            with self.with_mocked_pac_sign_success():
                picking.l10n_mx_edi_cfdi_try_send()

            self._assert_picking_cfdi(picking, 'test_delivery_guide_hazardous_product_outgoing')

    @freeze_time('2017-01-01')
    def test_delivery_guide_maybe_hazardous_product_outgoing_0(self):
        '''Test the delivery guide of a maybe (0,1) hazardous product
           Instance not hazardous
        '''
        self.product.write({
            'unspsc_code_id': self.env.ref('product_unspsc.unspsc_code_12352106').id,
            'l10n_mx_edi_hazardous_material_code': '0',
        })
        with self.mx_external_setup(self.frozen_today):
            warehouse = self._create_warehouse()
            picking = self._create_picking(warehouse)

            with self.with_mocked_pac_sign_success():
                picking.l10n_mx_edi_cfdi_try_send()

            self._assert_picking_cfdi(picking, 'test_delivery_guide_maybe_hazardous_product_outgoing_0')

    @freeze_time('2017-01-01')
    def test_delivery_guide_maybe_hazardous_product_outgoing_1(self):
        '''Test the delivery guide of a maybe (0,1) hazardous product
           Instance hazardous
        '''
        self.product.write({
            'unspsc_code_id': self.env.ref('product_unspsc.unspsc_code_12352106').id,
            'l10n_mx_edi_hazardous_material_code': '1052',
            'l10n_mx_edi_hazard_package_type': '1H1',
        })
        with self.mx_external_setup(self.frozen_today):
            warehouse = self._create_warehouse()
            picking = self._create_picking(warehouse)

            with self.with_mocked_pac_sign_success():
                picking.l10n_mx_edi_cfdi_try_send()

            self._assert_picking_cfdi(picking, 'test_delivery_guide_maybe_hazardous_product_outgoing_1')
