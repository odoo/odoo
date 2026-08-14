from odoo.exceptions import ValidationError
from odoo.tests import tagged
from . import common


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestResPartner(common.TestArCommon):

    def test_l10n_ar_cuit_number(self):
        with self.assertRaisesRegex(ValidationError, 'Invalid length for "CUIT"'):
            self.partner_ri.vat = "BE0477472701"
