from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEcResPartner(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('ec')
    def setUpClass(cls):
        super().setUpClass()
        cls.ec_ruc = cls.env.ref('l10n_ec.ec_ruc', False)
        cls.ec_dni = cls.env.ref('l10n_ec.ec_dni', False)
        cls.ec_partner = cls.env['res.partner'].create({
            'name': 'Ecuadorian Partner',
            'l10n_latam_identification_type_id': cls.ec_ruc.id,
            'country_id': cls.env.ref('base.ec').id,
        })

    def test_ec_partner_vat_validation(self):
        def assert_invalid_vat(vat):
            with self.assertRaises(ValidationError):
                self.ec_partner.vat = vat

        assert_invalid_vat('17100340650')
        assert_invalid_vat('171003406500A')

        self.ec_partner.write({
            'vat': '',
            'l10n_latam_identification_type_id': self.ec_dni.id,
        })
        assert_invalid_vat('1710034')
        assert_invalid_vat('171003406A')
