# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
_logger = logging.getLogger(__name__)

from odoo.tests import common
from odoo.exceptions import ValidationError
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

try:
    import vatnumber
except ImportError:
    _logger.warning("VAT validation partially unavailable because the `vatnumber` Python library cannot be found. "
    "Install it to support more countries, for example with `easy_install vatnumber`.")
    vatnumber = lambda: False
    vatnumber.check_vies = lambda: False  # dummy method for mock

class TestStructure(common.TransactionCase):

    def test_peru_ruc_format(self):
        """Only values that has the length of 11 will be checked as RUC, that's what we are proving. The second part
        will check for a valid ruc and there will be no problem at all.
        """
        partner = self.env['res.partner'].create({'name': "Dummy partner", 'country_id': self.env.ref('base.pe').id})

        with self.assertRaises(ValidationError):
            partner.vat = '11111111111'
        partner.vat = '20507822470'

    def test_parent_validation(self):
        """Test the validation with company and contact"""

        # disable the verification to set an invalid vat number
        self.env.user.company_id.vat_check_vies = False
        company = self.env["res.partner"].create({
            "name": "World Company",
            "country_id": self.env.ref("base.be").id,
            "vat": "ATU12345675",
            "company_type": "company",
        })
        contact = self.env["res.partner"].create({
            "name": "Sylvestre",
            "parent_id": company.id,
            "company_type": "person",
        })

        def mock_check_vies(vat_number):
            """ Fake vatnumber method that will only allow one number """
            return vat_number == 'BE0987654321'

        # reactivate it and correct the vat number
        with patch.object(vatnumber, 'check_vies', mock_check_vies):
            self.env.user.company_id.vat_check_vies = True
            company.vat = "BE0987654321"
