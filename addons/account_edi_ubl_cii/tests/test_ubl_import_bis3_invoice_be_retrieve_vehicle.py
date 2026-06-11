from odoo.addons.account_edi_ubl_cii.tests.test_ubl_import_bis3_invoice_be import TestUblImportBis3InvoiceBE
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3InvoiceBEVehicle(TestUblImportBis3InvoiceBE):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ensure_installed('fleet')
        # create car datas
        brand = cls.env['fleet.vehicle.model.brand'].sudo().create({  # noqa: OLS03001
            'name': 'Test Brand',
        })
        model = cls.env['fleet.vehicle.model'].sudo().create({  # noqa: OLS03001
            'name': 'Test Model',
            'brand_id': brand.id,
        })
        FleetVehicleSudo = cls.env['fleet.vehicle'].sudo()  # noqa: OLS03001
        cls.car = FleetVehicleSudo.create({
            'model_id': model.id,
            'vin_sn': 'ABCDEF012345GHJKL',
            'license_plate': '1-ABC-123',
        })
        cls.car2 = FleetVehicleSudo.create({
            'model_id': model.id,
            'vin_sn': 'ABCDEF012346GHJKL',
        })
        cls.car3 = FleetVehicleSudo.create({
            'model_id': model.id,
            'vin_sn': 'ABCDEF012347GHJKL',
        })

        cls.env.ref('base.EUR').active = True  # EU

    def test_vehicle_import_generic_invoice(self):
        """
        Test that we get the common value on the full invoice for each lines
        """
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_vehicle_invoice',
            journal=self.company_data['default_journal_sale'],
        )

        # One VIN SN for the move, all lines should link the vehicle
        self.assertRecordValues(invoice.invoice_line_ids, [{'vehicle_id': self.car.id} for _ in range(3)])

    def test_vehicle_import_different_lines(self):
        """
        Test that vehicle id is set on invoice lines if fleet is installed
        with each invoice line having its own defined value
        """
        # Multiple VIN SN, every line should link its own vehicle
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_vehicle_invoice_lines',
            journal=self.company_data['default_journal_sale'],
        )

        self.assertRecordValues(invoice.invoice_line_ids, [
            {'vehicle_id': self.car.id},  # match VIN in AdditionalItemProperty/Value where AdditionalItemProperty/Name == 'SerialNumber'
            {'vehicle_id': self.car2.id},  # match VIN in AdditionalItemProperty/Value where AdditionalItemProperty/Name == 'VIN'
            {'vehicle_id': self.car.id},  # match License Plate in AdditionalItemProperty/Value where AdditionalItemProperty/Name == 'PlateNumber'
            {'vehicle_id': self.car3.id},  # search VIN in Item/Description
            {'vehicle_id': self.car.id},  # search License Plate in Item/Description
            {'vehicle_id': self.car.id},  # search combined License Plate and VIN in Item/Description
            {'vehicle_id': False},  # Double vin -> no vehicle linked
        ])
