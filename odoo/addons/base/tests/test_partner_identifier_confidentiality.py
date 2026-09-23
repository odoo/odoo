from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.base.tests.common import converted_reach


@tagged("post_install", "-at_install")
class TestIdentifierConfidentiality(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Type = cls.env["res.partner.identifier.type"]
        cls.public_type = cls.Type.create({"name": "Loyalty Number", "code": "LOYALTY"})
        cls.secret_type = cls.Type.create(
            {"name": "National Number", "code": "NATIONAL", "confidential": True}
        )
        cls.reader = cls.env["res.users"].create(
            {
                "name": "Ordinary Reader",
                "login": "identifier_reader",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.other = cls.env["res.partner"].create({"name": "Someone Else"})
        cls.own_public = cls.env["res.partner.identifier"].create(
            {
                "partner_id": cls.reader.partner_id.id,
                "type_id": cls.public_type.id,
                "value": "L-1",
            }
        )
        cls.own_secret = cls.env["res.partner.identifier"].create(
            {
                "partner_id": cls.reader.partner_id.id,
                "type_id": cls.secret_type.id,
                "value": "N-1",
            }
        )
        cls.other_public = cls.env["res.partner.identifier"].create(
            {"partner_id": cls.other.id, "type_id": cls.public_type.id, "value": "L-2"}
        )
        cls.other_secret = cls.env["res.partner.identifier"].create(
            {"partner_id": cls.other.id, "type_id": cls.secret_type.id, "value": "N-2"}
        )

    def _visible_to_reader(self):
        return self.env["res.partner.identifier"].with_user(self.reader).search([])

    def test_another_contacts_confidential_identifier_is_not_readable(self):
        self.assertNotIn(self.other_secret, self._visible_to_reader())

    def test_a_non_confidential_identifier_stays_readable_by_everyone(self):
        self.assertIn(self.other_public, self._visible_to_reader())

    def test_the_subject_reads_their_own_confidential_identifier(self):
        self.assertIn(self.own_secret, self._visible_to_reader())
        self.assertIn(self.own_public, self._visible_to_reader())

    def test_reading_the_value_directly_raises_rather_than_returning_it(self):
        with self.assertRaises(AccessError):
            self.other_secret.with_user(self.reader).read(["value"])

    def test_the_rule_is_a_no_op_for_identifiers_of_unmarked_types(self):
        self.assertFalse(self.public_type.confidential)
        everything = self.env["res.partner.identifier"].search(
            [("type_id", "=", self.public_type.id)]
        )
        self.assertEqual(
            everything,
            everything.with_user(self.reader).search(
                [("type_id", "=", self.public_type.id)]
            ),
        )


@tagged("post_install", "-at_install")
class TestIdentifierContactCreation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        secret_type = cls.env["res.partner.identifier.type"].create(
            {"name": "Social Security", "code": "SSN_T", "confidential": True}
        )
        public_type = cls.env["res.partner.identifier.type"].create(
            {"name": "Supplier Code", "code": "SUPPLIER_T"}
        )
        cls.creator = cls.env["res.users"].create(
            {
                "name": "Contact Creator",
                "login": "identifier_contact_creator",
                "group_ids": [
                    (4, cls.env.ref("base.group_user").id),
                    (4, cls.env.ref("base.group_partner_manager").id),
                ],
            }
        )
        other = cls.env["res.partner"].create({"name": "Another Person"})
        Identifier = cls.env["res.partner.identifier"]
        cls.own_secret = Identifier.create(
            {
                "partner_id": cls.creator.partner_id.id,
                "type_id": secret_type.id,
                "value": "S-1",
            }
        )
        cls.other_public = Identifier.create(
            {"partner_id": other.id, "type_id": public_type.id, "value": "P-2"}
        )
        cls.other_secret = Identifier.create(
            {"partner_id": other.id, "type_id": secret_type.id, "value": "S-2"}
        )
        cls.scope = cls.own_secret | cls.other_public | cls.other_secret

    def test_contact_creation_does_not_read_confidential_identifiers(self):
        visible = self.scope.with_user(self.creator).search(
            [("id", "in", self.scope.ids)]
        )
        self.assertEqual(visible, self.own_secret | self.other_public)

    def test_the_converted_permission_keeps_contact_creation_scoped(self):
        for operation in ("read", "write", "unlink"):
            with self.subTest(operation=operation):
                reached = converted_reach(
                    self.env, "res.partner.identifier", self.creator, operation
                )
                self.assertEqual(
                    reached & self.scope, self.own_secret | self.other_public
                )


@tagged("post_install", "-at_install")
class TestPrivateAddressType(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.partner"].create(
            {"name": "Acme Corp", "is_company": True, "city": "Metropolis"}
        )
        cls.home = cls.env["res.partner"].create(
            {
                "parent_id": cls.company.id,
                "type": "private",
                "street": "Home 1",
                "city": "Smallville",
            }
        )

    def test_a_private_address_is_a_selectable_type(self):
        self.assertEqual(self.home.type, "private")

    def test_its_own_label_is_not_the_generic_one(self):
        self.assertEqual(self.home.type_address_label, "Private Address")

    def test_it_is_distinguishable_in_the_complete_name(self):
        self.assertIn("private", self.env["res.partner"]._complete_name_displayed_types)
        self.assertNotEqual(self.home.complete_name, self.company.complete_name)

    def test_the_parent_does_not_overwrite_a_private_address(self):
        self.company.write({"street": "Corporate Plaza", "city": "Metropolis"})
        self.home.invalidate_recordset()
        self.assertEqual(self.home.street, "Home 1")
        self.assertEqual(self.home.city, "Smallville")

    def test_a_private_address_does_not_push_up_onto_its_parent(self):
        self.home.write({"street": "Home 2", "city": "Bludhaven"})
        self.company.invalidate_recordset()
        self.assertNotEqual(self.company.street, "Home 2")
        self.assertNotEqual(self.company.city, "Bludhaven")

    def test_address_get_does_not_hand_out_a_private_address_by_default(self):
        found = self.company.address_get(["delivery"])
        self.assertNotIn(self.home.id, found.values())
