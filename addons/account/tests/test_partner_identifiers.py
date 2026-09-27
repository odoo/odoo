from odoo.exceptions import ValidationError
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestAccountPartnerIdentifiers(TransactionCase):

    def test_identifier_proxy_gln(self):
        """ Test the "proxy" field (compute/inverse on the JSON) behavior. """
        partner = self.env['res.partner'].create({
            'name': 'Test Partner GLN',
            'country_id': self.env.ref('base.fr').id,
        })

        partner.global_location_number = '9780471117094'
        self.assertEqual(partner.additional_identifiers, {'EAN_GLN': '9780471117094'})
        partner.global_location_number = False
        self.assertFalse(partner.additional_identifiers)

        partner._set_additional_identifier('EAN_GLN', '9780471117094')
        self.assertEqual(partner.additional_identifiers, {'EAN_GLN': '9780471117094'})
        partner.global_location_number = ''
        self.assertFalse(partner.additional_identifiers)

        with self.assertRaisesRegex(ValidationError, "Invalid identifier"):
            partner.global_location_number = 'wrong_gln'

    def test_retrieve_partner_by_additional_identifiers(self):
        """ `_retrieve_partner` matches on `additional_identifiers`, ignores an empty value,
        and lets the identifier take precedence over a weaker (name) match. """
        Partner = self.env['res.partner']
        partner = Partner.create({
            'name': "Acme Corp",
            'additional_identifiers': {'BE_EN': '0123456749'},
        })

        # Match on the identifier alone.
        self.assertEqual(Partner._retrieve_partner(additional_identifiers={'BE_EN': '0123456749'}), partner)
        # A non-matching identifier returns nothing.
        self.assertFalse(Partner._retrieve_partner(additional_identifiers={'BE_EN': '0000000000'}))
        # An empty/missing mapping is ignored
        self.assertFalse(Partner._retrieve_partner(additional_identifiers={}))
        self.assertFalse(Partner._retrieve_partner(additional_identifiers=None))

        # The identifier takes precedence over a name-only twin
        name_twin = Partner.create({'name': "Acme Corp"})
        self.assertEqual(Partner._retrieve_partner(name="Acme Corp"), name_twin)
        self.assertEqual(
            Partner._retrieve_partner(name="Acme Corp", additional_identifiers={'BE_EN': '0123456749'}),
            partner,
        )
