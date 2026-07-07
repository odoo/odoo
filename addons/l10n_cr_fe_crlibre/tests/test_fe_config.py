from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestFeConfig(TransactionCase):

    def setUp(self):
        super().setUp()
        self.config = self.env['l10n_cr.fe.config'].create({
            'company_id': self.env.company.id,
            'environment': 'stag',
            'identification_type': '01',
            'identification_number': '208400858',
            'legal_name': 'Empresa Demo SA',
            'economic_activity_code': '011101',
            'province': '1', 'canton': '01', 'district': '08', 'neighborhood': '01',
            'address_detail': 'Local de prueba',
            'phone': '22220000', 'email': 'demo@empresa.cr',
            'hacienda_username': 'user@stag.comprobanteselectronicos.go.cr',
            'hacienda_password': 'secret',
            'certificate_pin': '1234',
        })

    def test_get_for_company_returns_config(self):
        found = self.env['l10n_cr.fe.config']._get_for_company(self.env.company)
        self.assertEqual(found, self.config)

    def test_get_for_company_raises_when_missing(self):
        other_company = self.env['res.company'].create({'name': 'Otra Empresa'})
        with self.assertRaises(UserError):
            self.env['l10n_cr.fe.config']._get_for_company(other_company)

    def test_company_id_is_unique(self):
        with self.assertRaises(Exception):
            self.env['l10n_cr.fe.config'].create({
                'company_id': self.env.company.id,
                'environment': 'stag',
                'identification_type': '01',
                'identification_number': '111111111',
                'legal_name': 'Otra Empresa SA',
                'economic_activity_code': '011101',
                'province': '1', 'canton': '01', 'district': '08', 'neighborhood': '01',
                'address_detail': 'Otro local',
                'email': 'otro@empresa.cr',
            })

    def test_restricted_fields_hidden_from_non_admin(self):
        plain_user = self.env['res.users'].create({
            'name': 'Usuario Normal', 'login': 'usuario_normal_fe_test',
        })
        self.env.ref('base.group_user').write({'user_ids': [(4, plain_user.id)]})
        with self.assertRaises(AccessError):
            self.config.with_user(plain_user).read(['hacienda_password'])

    def test_next_consecutivo_has_no_gaps(self):
        first = self.config._l10n_cr_fe_next_consecutivo()
        second = self.config._l10n_cr_fe_next_consecutivo()
        self.assertEqual(len(first), 10)
        self.assertEqual(int(second), int(first) + 1)

    def test_next_consecutivo_independent_per_company(self):
        other_company = self.env['res.company'].create({'name': 'Otra Empresa FE'})
        other_config = self.env['l10n_cr.fe.config'].create({
            'company_id': other_company.id,
            'environment': 'stag', 'identification_type': '01',
            'identification_number': '999999999', 'legal_name': 'Otra SA',
            'economic_activity_code': '011101',
            'province': '1', 'canton': '01', 'district': '01', 'neighborhood': '01',
            'address_detail': 'x', 'email': 'x@x.cr',
        })
        first_this = self.config._l10n_cr_fe_next_consecutivo()
        first_other = other_config._l10n_cr_fe_next_consecutivo()
        second_this = self.config._l10n_cr_fe_next_consecutivo()
        second_other = other_config._l10n_cr_fe_next_consecutivo()
        # Each company's sequence is independent, starting from 1
        self.assertEqual(first_this, '0000000001')
        self.assertEqual(first_other, '0000000001')
        self.assertEqual(second_this, '0000000002')
        self.assertEqual(second_other, '0000000002')
