from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPrivateAddressAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env["res.partner"]

        cls.reader = cls.env["res.users"].create(
            {
                "name": "Ordinary Reader",
                "login": "private_address_reader",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.manager = cls.env["res.users"].create(
            {
                "name": "Contact Manager",
                "login": "private_address_manager",
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("base.group_partner_manager").id,
                        ],
                    )
                ],
            }
        )
        cls.subject = Partner.create({"name": "Subject Person"})
        cls.subject_home = Partner.create(
            {
                "parent_id": cls.subject.id,
                "type": "private",
                "street": "12 Rue Confidentielle",
                "city": "Brussels",
            }
        )
        cls.reader_home = Partner.create(
            {
                "parent_id": cls.reader.partner_id.id,
                "type": "private",
                "street": "3 Own Street",
                "city": "Ghent",
            }
        )
        cls.ordinary_child = Partner.create(
            {
                "parent_id": cls.subject.id,
                "type": "delivery",
                "street": "Warehouse Dock 4",
                "city": "Antwerp",
            }
        )

    def _visible(self):
        return self.env["res.partner"].with_user(self.reader).search([])

    def test_another_persons_private_address_is_not_readable(self):
        self.assertNotIn(self.subject_home, self._visible())

    def test_the_subject_reads_their_own_private_address(self):
        self.assertIn(self.reader_home, self._visible())

    def test_the_person_themselves_stays_readable(self):
        self.assertIn(self.subject, self._visible())

    def test_an_ordinary_address_of_the_same_parent_stays_readable(self):
        self.assertIn(self.ordinary_child, self._visible())

    def test_the_rule_does_not_narrow_ordinary_contacts(self):
        as_superuser = self.env["res.partner"].search([("type", "!=", "private")])
        as_reader = (
            self.env["res.partner"]
            .with_user(self.reader)
            .search([("type", "!=", "private")])
        )
        self.assertEqual(as_superuser, as_reader)

    def test_reading_the_columns_directly_is_refused_too(self):
        with self.assertRaises(AccessError):
            self.subject_home.with_user(self.reader).read(["street", "city"])

    def test_a_contact_manager_cannot_delete_another_persons_private_address(self):
        with self.assertRaises(AccessError):
            self.subject_home.with_user(self.manager).unlink()
        self.assertTrue(self.subject_home.exists())

    def test_the_subject_deletes_their_own_private_address(self):
        own = self.env["res.partner"].create(
            {
                "parent_id": self.manager.partner_id.id,
                "type": "private",
                "street": "9 Removable Lane",
            }
        )
        own.with_user(self.manager).unlink()
        self.assertFalse(own.exists())

    def test_a_contact_manager_still_deletes_an_ordinary_address(self):
        other = self.env["res.partner"].create(
            {"parent_id": self.subject.id, "type": "delivery", "street": "Dock 5"}
        )
        other.with_user(self.manager).unlink()
        self.assertFalse(other.exists())

    def test_the_rule_is_global_and_must_stay_global(self):
        rule = self.env.ref("base.res_partner_private_address_rule")
        self.assertEqual(rule.kind, "guard")
        self.assertEqual(rule.guard_scope, "everyone")
        self.assertEqual(rule.group_id, self.env.ref("base.group_everyone"))

    def test_the_domain_names_parent_id_rather_than_child_of(self):
        rule = self.env.ref("base.res_partner_private_address_rule")
        self.assertIn("parent_id", rule.domain)
        self.assertNotIn("child_of", rule.domain)
