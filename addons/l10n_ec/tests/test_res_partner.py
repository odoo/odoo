from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestResPartner(TransactionCase):

    @classmethod
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
        def assert_invalid_vat(vat, message):
            with self.assertRaisesRegex(ValidationError, message):
                self.ec_partner.vat = vat

        ruc_message = r"RUC.*13 digits"
        assert_invalid_vat('17100340650', ruc_message)
        assert_invalid_vat('171003406500A', ruc_message)

        self.ec_partner.write({
            'vat': '',
            'l10n_latam_identification_type_id': self.ec_dni.id,
        })
        dni_message = r"Citizenship.*10 digits"
        assert_invalid_vat('1710034', dni_message)
        assert_invalid_vat('171003406A', dni_message)
