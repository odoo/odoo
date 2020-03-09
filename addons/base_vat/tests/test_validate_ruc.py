# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import common
from odoo.exceptions import ValidationError


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
            "country_id": self.env.ref("base.at").id,
            "vat": "ATU12345675",
            "company_type": "company",
        })
        contact = self.env["res.partner"].create({
            "name": "Sylvestre",
            "parent_id": company.id,
            "company_type": "person",
        })

        # reactivate it and correct the vat number
        self.env.user.company_id.vat_check_vies = True
        company.vat = "ATU69245667"
