from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPlResPartner(BaseCommon):
    _test_user_groups = ('base.group_user', 'base.group_partner_manager')

    def test_krs_number(self):
        partner = self.env['res.partner'].create({
            'name': "PL partner",
            'country_id': self.env.ref('base.pl').id,
            'additional_identifiers': {'PL_KRS': '0000 123 456'},
        })
        self.assertEqual(partner._get_additional_identifier('PL_KRS'), '0000123456')

        for invalid_krs in ('123456', '00001234567', '000012345A'):
            with self.subTest(krs=invalid_krs), self.assertRaises(ValidationError):
                partner.additional_identifiers = {'PL_KRS': invalid_krs}
