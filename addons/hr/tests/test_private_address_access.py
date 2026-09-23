from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPrivateAddressAccess(TransactionCase):
    """The employee path that produces the row, and how HR still reaches it.

    `base` withdraws every private address from everyone but its subject, with
    one GLOBAL rule scoped to `perm_read`. `hr` adds no rule of its own, and
    that is a decision rather than an omission: a group rule cannot lift a
    global one -- group domains OR among themselves and are then ANDed with the
    globals -- so an `hr.group_hr_user` rule granting everything would have
    granted the officer nothing, while being permissive enough to OR away any
    other group-scoped restriction on res.partner.

    An HR officer reaches the address the way the product intends instead:
    through `hr.employee.private_*`, which are `related` onto the row and carry
    `groups="hr.group_hr_user"`. Related traversal is sudo by default, so the
    column ACL is the gate and the row rule never has to make an exception.

    Every read goes through `with_user` -- `TransactionCase` runs as superuser,
    where `env.su` skips record rules and every assertion below would pass
    against no rule at all.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        internal = cls.env.ref("base.group_user")
        hr_user = cls.env.ref("hr.group_hr_user")

        cls.colleague = cls.env["res.users"].create(
            {
                "name": "Ordinary Colleague",
                "login": "hr_private_colleague",
                "group_ids": [(6, 0, [internal.id])],
            }
        )
        cls.officer = cls.env["res.users"].create(
            {
                "name": "HR Officer",
                "login": "hr_private_officer",
                "group_ids": [(6, 0, [internal.id, hr_user.id])],
            }
        )
        cls.subject = cls.env["res.users"].create(
            {
                "name": "Subject Person",
                "login": "hr_private_subject",
                "group_ids": [(6, 0, [internal.id])],
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Subject Person",
                "partner_id": cls.subject.partner_id.id,
                "user_id": cls.subject.id,
                "company_id": cls.env.company.id,
            }
        )
        cls.employee.write(
            {
                "private_street": "12 Rue Confidentielle",
                "private_city": "Brussels",
                "private_zip": "1000",
            }
        )
        cls.env.flush_all()
        cls.home = cls.employee.sudo().private_address_id

    def _finds_home(self, user):
        return bool(
            self.env["res.partner"]
            .with_user(user)
            .search_count([("id", "=", self.home.id)])
        )

    def test_the_row_the_employee_form_writes_to_actually_exists(self):
        """Guards the fixture: every assertion below is vacuous without it."""
        self.assertTrue(self.home)
        self.assertEqual(self.home.type, "private")
        self.assertEqual(self.home.street, "12 Rue Confidentielle")

    def test_a_colleague_cannot_find_the_home_address(self):
        self.assertFalse(self._finds_home(self.colleague))

    def test_a_colleague_cannot_read_it_through_the_employee_either(self):
        """Both gates are in force; neither one alone was enough."""
        with self.assertRaises(AccessError):
            self.employee.with_user(self.colleague).private_street

    def test_the_employee_finds_their_own(self):
        self.assertTrue(self._finds_home(self.subject))

    def test_an_hr_officer_reads_it_through_the_employee(self):
        """The purpose-built path, and the only one an officer needs."""
        self.assertEqual(
            self.employee.with_user(self.officer).private_street,
            "12 Rue Confidentielle",
        )

    def test_an_hr_officer_still_cannot_trawl_for_home_addresses(self):
        """Least privilege: reading one employee's address is not a search.

        If HR ever needs the list, that is an action on `hr.employee` with the
        column ACL doing the gating -- not a widening of who may read
        res.partner rows.
        """
        self.assertFalse(self._finds_home(self.officer))

    def test_a_restrictive_group_guard_on_res_partner_still_denies(self):
        """The property the first draft of this fix destroyed.

        Permissions OR. A permissive `base.group_user` row on res.partner --
        which is what "let the subject see their own private address" looks
        like when it is group-scoped -- would OR away nothing a guard states:
        a restriction on a group's members is a guard, and no permission
        lifts it. This test states it from the hr side because hr is where
        private rows exist.
        """
        ordinary = self.env["res.partner"].create({"name": "Ordinary Contact"})
        self.env["ir.access"].create(
            {
                "name": "deny everything to internal users",
                "model_id": self.env.ref("base.model_res_partner").id,
                "group_id": self.env.ref("base.group_user").id,
                "kind": "guard",
                "guard_scope": "members",
                "operation": "crud",
                # hides every row; a FALSE guard would deny the model instead
                "domain": "[('id', '<', 0)]",
            }
        )
        self.env.flush_all()
        self.env.registry.clear_cache()
        self.assertFalse(
            self.env["res.partner"]
            .with_user(self.colleague)
            .search_count([("id", "=", ordinary.id)])
        )

    def test_get_all_addr_stops_offering_the_home_address_to_a_colleague(self):
        """`_get_all_addr` is the one real consumer of these rows.

        It filters `child_ids`, so the rule reaches it without a change here: a
        colleague gets the work contact's own addresses and no home address,
        and no error. That restores what the code did before the address became
        a row -- it read `employee_id.private_street`, a `groups=`-gated
        column, so a non-HR caller never obtained a home address either.

        `account_batch_payment` calls this through `sudo()` and is unaffected;
        `account_iso20022` does not, and now falls back to the work contact's
        own address for a caller who is not the subject.
        """
        contact = self.subject.partner_id
        addresses = contact.with_user(self.colleague)._get_all_addr()
        self.assertNotIn("employee", [a["contact_type"] for a in addresses])

    def test_get_all_addr_still_offers_it_to_the_subject(self):
        contact = self.subject.partner_id
        addresses = contact.with_user(self.subject)._get_all_addr()
        home = [a for a in addresses if a["contact_type"] == "employee"]
        self.assertEqual(len(home), 1)
        self.assertEqual(home[0]["street"], "12 Rue Confidentielle")

    def test_hr_ships_no_read_of_its_own_on_res_partner(self):
        """Pins the decision in the class docstring against a well-meant re-add."""
        reads = self.env["ir.access"].search(
            [
                ("model_id", "=", self.env.ref("base.model_res_partner").id),
                ("for_read", "=", True),
            ]
        )
        from_hr = self.env["ir.model.data"].search(
            [
                ("model", "=", "ir.access"),
                ("module", "=", "hr"),
                ("res_id", "in", reads.ids),
            ]
        )
        self.assertFalse(
            from_hr.mapped("name"),
            "hr must not add a read of res.partner: no permission lifts base's "
            "guard on private addresses, and a permissive one only widens.",
        )
