# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import Command
from odoo.addons.l10n_mx_edi.tests.common import EXTERNAL_MODE
from odoo.tests import tagged
from .common import TestMXEdiStockCommon


@tagged('post_install_l10n', 'post_install', '-at_install', *(['-standard', 'external'] if EXTERNAL_MODE else []))
class TestCFDIPickingXml(TestMXEdiStockCommon):

    def test_delivery_guide_outgoing(self):
        with self.mx_external_setup(self.frozen_today):
            warehouse = self._create_warehouse()
            picking = self._create_picking(warehouse)

            with self.with_mocked_pac_sign_success():
                picking.l10n_mx_edi_cfdi_try_send()

            self._assert_picking_cfdi(picking, 'test_delivery_guide_outgoing')

    def test_delivery_guide_incoming(self):
        with self.mx_external_setup(self.frozen_today):
            warehouse = self._create_warehouse()
            picking = self._create_picking(warehouse, outgoing=False)

            with self.with_mocked_pac_sign_success():
                picking.l10n_mx_edi_cfdi_try_send()

            self._assert_picking_cfdi(picking, 'test_delivery_guide_incoming')

    def test_delivery_guide_company_branch(self):
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
        branch.partner_id.write({
            'street_name': self.env.company.partner_id.street_name,
            'street_number': self.env.company.partner_id.street_number,
            'street_number2': self.env.company.partner_id.street_number2,
            'city_id': self.env.company.partner_id.city_id.id,
        })
        self.product.company_id = branch
        with self.mx_external_setup(self.frozen_today - relativedelta(hours=1)):
            warehouse = self._create_warehouse(company_id=branch.id, partner_id=branch.partner_id.id)
            picking = self._create_picking(warehouse)

            with self.with_mocked_pac_sign_success():
                picking.l10n_mx_edi_cfdi_try_send()
            self._assert_picking_cfdi(picking, 'test_delivery_guide_company_branch')

    def test_delivery_guide_comex_outgoing(self):
        self.product.l10n_mx_edi_material_type = '05'
        self.product.l10n_mx_edi_material_description = 'Test material description'

        with self.mx_external_setup(self.frozen_today):
            warehouse = self._create_warehouse()
            picking = self._create_picking(
                warehouse,
                picking_vals={
                    'partner_id': self.partner_us.id,
                    'l10n_mx_edi_customs_document_type_id': self.env.ref('l10n_mx_edi_stock_extended_30.l10n_mx_edi_customs_document_type_02').id,
                    'l10n_mx_edi_customs_doc_identification': '0123456789',
                    'l10n_mx_edi_customs_regime_id': self.custom_regime_exd.id,
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
                    'l10n_mx_edi_customs_document_type_id': self.env.ref('l10n_mx_edi_stock_extended_30.l10n_mx_edi_customs_document_type_01').id,
                    'l10n_mx_edi_importer_id': self.partner_mx.id,
                    'l10n_mx_edi_customs_regime_id': self.custom_regime_imd.id,
                    'l10n_mx_edi_pedimento_number': "15  48  3009  0001234",
                },
            )

            with self.with_mocked_pac_sign_success():
                picking.l10n_mx_edi_cfdi_try_send()

            self._assert_picking_cfdi(picking, 'test_delivery_guide_comex_incoming')
