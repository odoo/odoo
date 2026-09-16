from unittest.mock import patch
from urllib.parse import urlparse

from markupsafe import Markup
from psycopg.errors import IntegrityError

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged, users
from odoo.tests.common import HttpCase
from odoo.tools import mute_logger

from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools.discuss import Store


@tagged("mail_followers")
class BaseFollowersTest(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_record = (
            cls.env["mail.test.simple"]
            .with_context(cls._test_context)
            .create({"name": "Test", "email_from": "ignasse@example.com"})
        )
        cls._create_portal_user()

        Subtype = cls.env["mail.message.subtype"]
        # global
        cls.mt_al_def = Subtype.create(
            {"name": "mt_al_def", "default": True, "res_model": False}
        )
        cls.mt_al_nodef = Subtype.create(
            {"name": "mt_al_nodef", "default": False, "res_model": False}
        )
        # mail.test.simple
        cls.mt_mg_def = Subtype.create(
            {"name": "mt_mg_def", "default": True, "res_model": "mail.test.simple"}
        )
        cls.mt_mg_nodef = Subtype.create(
            {"name": "mt_mg_nodef", "default": False, "res_model": "mail.test.simple"}
        )
        cls.mt_mg_def_int = Subtype.create(
            {
                "name": "mt_mg_def",
                "default": True,
                "res_model": "mail.test.simple",
                "internal": True,
            }
        )
        # mail.test.container
        cls.mt_cl_def = Subtype.create(
            {"name": "mt_cl_def", "default": True, "res_model": "mail.test.container"}
        )

        cls.default_group_subtypes = Subtype.search(
            [
                ("default", "=", True),
                "|",
                ("res_model", "=", "mail.test.simple"),
                ("res_model", "=", False),
            ]
        )
        cls.default_group_subtypes_portal = Subtype.search(
            [
                ("internal", "=", False),
                ("default", "=", True),
                "|",
                ("res_model", "=", "mail.test.simple"),
                ("res_model", "=", False),
            ]
        )

    def test_field_message_is_follower(self):
        test_record = self.test_record.with_user(self.user_employee)
        followed_before = test_record.search([("message_is_follower", "=", True)])
        self.assertFalse(test_record.message_is_follower)
        test_record.message_subscribe(partner_ids=[self.user_employee.partner_id.id])
        followed_after = test_record.search([("message_is_follower", "=", True)])
        self.assertTrue(test_record.message_is_follower)
        self.assertEqual(followed_before | test_record, followed_after)

    def test_field_message_partner_ids(self):
        test_record = self.test_record.with_user(self.user_employee)
        partner = self.user_employee.partner_id
        followed_before = self.env["mail.test.simple"].search(
            [("message_partner_ids", "in", partner.ids)]
        )
        self.assertFalse(partner in test_record.message_partner_ids)
        self.assertNotIn(test_record, followed_before)
        test_record.message_subscribe(partner_ids=[partner.id])
        followed_after = self.env["mail.test.simple"].search(
            [("message_partner_ids", "in", partner.ids)]
        )
        self.assertTrue(partner in test_record.message_partner_ids)
        self.assertEqual(followed_before + test_record, followed_after)
        # `message_partner_ids` carries groups="base.group_user", so the FIELD
        # ACL refuses a portal user before `_search_message_partner_ids` runs.
        # That guard is a second line of defence, not the operative policy, and
        # asserting its message here asserted a string no portal user can ever
        # reach -- upstream 19.0 carries the same unreachable pair.
        with self.assertRaisesRegex(AccessError, "message_partner_ids"):
            self.env["mail.test.simple"].with_user(self.user_portal).search(
                [("message_partner_ids", "in", partner.ids)]
            )

    def test_field_followers(self):
        test_record = self.test_record.with_user(self.user_employee)
        test_record.message_subscribe(
            partner_ids=[
                self.user_employee.partner_id.id,
                self.user_admin.partner_id.id,
            ]
        )
        followers = self.env["mail.followers"].search(
            [("res_model", "=", "mail.test.simple"), ("res_id", "=", test_record.id)]
        )
        self.assertEqual(followers, test_record.message_follower_ids)
        self.assertEqual(
            test_record.message_partner_ids,
            self.user_employee.partner_id | self.user_admin.partner_id,
        )

    def test_followers_subtypes_default(self):
        test_record = self.test_record.with_user(self.user_employee)
        test_record.message_subscribe(partner_ids=[self.user_employee.partner_id.id])
        self.assertEqual(test_record.message_partner_ids, self.user_employee.partner_id)
        follower = self.env["mail.followers"].search(
            [
                ("res_model", "=", "mail.test.simple"),
                ("res_id", "=", test_record.id),
                ("partner_id", "=", self.user_employee.partner_id.id),
            ]
        )
        self.assertEqual(follower, test_record.message_follower_ids)
        self.assertEqual(follower.subtype_ids, self.default_group_subtypes)

    def test_followers_subtypes_default_internal(self):
        test_record = self.test_record.with_user(self.user_employee)
        test_record.message_subscribe(partner_ids=[self.partner_portal.id])
        self.assertEqual(test_record.message_partner_ids, self.partner_portal)
        follower = self.env["mail.followers"].search(
            [
                ("res_model", "=", "mail.test.simple"),
                ("res_id", "=", test_record.id),
                ("partner_id", "=", self.partner_portal.id),
            ]
        )
        self.assertEqual(follower.subtype_ids, self.default_group_subtypes_portal)

    def test_followers_subtypes_specified(self):
        test_record = self.test_record.with_user(self.user_employee)
        test_record.message_subscribe(
            partner_ids=[self.user_employee.partner_id.id],
            subtype_ids=[self.mt_mg_nodef.id],
        )
        self.assertEqual(test_record.message_partner_ids, self.user_employee.partner_id)
        follower = self.env["mail.followers"].search(
            [
                ("res_model", "=", "mail.test.simple"),
                ("res_id", "=", test_record.id),
                ("partner_id", "=", self.user_employee.partner_id.id),
            ]
        )
        self.assertEqual(follower, test_record.message_follower_ids)
        self.assertEqual(follower.subtype_ids, self.mt_mg_nodef)

    def test_followers_multiple_subscription_force(self):
        test_record = self.test_record.with_user(self.user_employee)

        test_record.message_subscribe(
            partner_ids=[self.user_admin.partner_id.id],
            subtype_ids=[self.mt_mg_nodef.id],
        )
        self.assertEqual(test_record.message_partner_ids, self.user_admin.partner_id)
        self.assertEqual(test_record.message_follower_ids.subtype_ids, self.mt_mg_nodef)

        test_record.message_subscribe(
            partner_ids=[self.user_admin.partner_id.id],
            subtype_ids=[self.mt_mg_nodef.id, self.mt_al_nodef.id],
        )
        self.assertEqual(test_record.message_partner_ids, self.user_admin.partner_id)
        self.assertEqual(
            test_record.message_follower_ids.subtype_ids,
            self.mt_mg_nodef | self.mt_al_nodef,
        )

    def test_followers_multiple_subscription_noforce(self):
        """Calling message_subscribe without subtypes on an existing subscription should not do anything (default < existing)"""
        test_record = self.test_record.with_user(self.user_employee)

        test_record.message_subscribe(
            partner_ids=[self.user_admin.partner_id.id],
            subtype_ids=[self.mt_mg_nodef.id, self.mt_al_nodef.id],
        )
        self.assertEqual(test_record.message_partner_ids, self.user_admin.partner_id)
        self.assertEqual(
            test_record.message_follower_ids.subtype_ids,
            self.mt_mg_nodef | self.mt_al_nodef,
        )

        # set new subtypes with force=False, meaning no rewriting of the subscription is done -> result should not change
        test_record.message_subscribe(partner_ids=[self.user_admin.partner_id.id])
        self.assertEqual(test_record.message_partner_ids, self.user_admin.partner_id)
        self.assertEqual(
            test_record.message_follower_ids.subtype_ids,
            self.mt_mg_nodef | self.mt_al_nodef,
        )

    def test_followers_multiple_subscription_update(self):
        """Calling message_subscribe with subtypes on an existing subscription should replace them (new > existing)"""
        test_record = self.test_record.with_user(self.user_employee)
        test_record.message_subscribe(
            partner_ids=[self.user_employee.partner_id.id],
            subtype_ids=[self.mt_mg_def.id, self.mt_cl_def.id],
        )
        self.assertEqual(test_record.message_partner_ids, self.user_employee.partner_id)
        follower = self.env["mail.followers"].search(
            [
                ("res_model", "=", "mail.test.simple"),
                ("res_id", "=", test_record.id),
                ("partner_id", "=", self.user_employee.partner_id.id),
            ]
        )
        self.assertEqual(follower, test_record.message_follower_ids)
        self.assertEqual(follower.subtype_ids, self.mt_mg_def | self.mt_cl_def)

        # remove one subtype `mt_mg_def` and set new subtype `mt_al_def`
        test_record.message_subscribe(
            partner_ids=[self.user_employee.partner_id.id],
            subtype_ids=[self.mt_cl_def.id, self.mt_al_def.id],
        )
        self.assertEqual(follower.subtype_ids, self.mt_cl_def | self.mt_al_def)

    @users("employee")
    def test_followers_inactive(self):
        """Test standard API does not subscribe inactive partners"""
        customer = self.env["res.partner"].create(
            {
                "name": "Valid Lelitre",
                "email": "valid.lelitre@agrolait.com",
                "country_id": self.env.ref("base.be").id,
                "phone_ids": [
                    Command.create({"number": "0456001122", "type": "landline"})
                ],
                "active": False,
            }
        )
        document = self.env["mail.test.simple"].browse(self.test_record.id)
        self.assertEqual(document.message_partner_ids, self.env["res.partner"])
        document.message_subscribe(partner_ids=(self.partner_portal | customer).ids)
        self.assertEqual(document.message_partner_ids, self.partner_portal)
        self.assertEqual(document.message_follower_ids.partner_id, self.partner_portal)

        # works through low-level API
        document._message_subscribe(partner_ids=(self.partner_portal | customer).ids)
        self.assertEqual(
            document.message_partner_ids,
            self.partner_portal,
            "No active test: customer not visible",
        )
        self.assertEqual(
            document.message_follower_ids.partner_id, self.partner_portal | customer
        )

    @users("employee")
    def test_followers_subtypes_archived_customer(self):
        """An archived customer is still a customer.

        `_get_get_subtypes` looked its customers up with a plain `search`,
        so `active_test` dropped the archived ones and they fell through to the
        *internal* default subtypes -- the branch reserved for employees. The
        low-level `_message_subscribe` subscribes archived partners on purpose
        (see `test_followers_inactive`), so the path is reached by design.
        """
        customer = (
            self.env["res.partner"]
            .sudo()
            .create(
                {
                    "active": False,
                    "email": "archived.customer@test.example.com",
                    "name": "Archived Customer",
                }
            )
        )
        self.assertTrue(customer.partner_share)
        document = self.env["mail.test.simple"].browse(self.test_record.id)
        document._message_subscribe(partner_ids=customer.ids)

        follower = (
            self.env["mail.followers"]
            .sudo()
            .search(
                [
                    ("res_model", "=", "mail.test.simple"),
                    ("res_id", "=", document.id),
                    ("partner_id", "=", customer.id),
                ]
            )
        )
        self.assertEqual(follower.subtype_ids, self.default_group_subtypes_portal)
        self.assertNotIn(self.mt_mg_def_int, follower.subtype_ids)

    def test_followers_subtypes_independent_of_subscriber(self):
        """The subtypes a partner gets depend on the partner, not on the caller.

        `_get_get_subtypes` asked `default_subtypes` unsudoed, and
        `mail.message.subtype` carries a record rule hiding internal subtypes
        from portal and public users. So the *same* internal partner, subscribed
        to the *same* record, came out with strictly fewer subtypes when a share
        user did the subscribing -- and stayed that way, silently, until someone
        re-subscribed them from an internal session.

        The path is ordinary: `/mail/thread/subscribe` is `auth="user"`, portal
        users included, and the controller calls `message_subscribe` with no
        `sudo()`. Six internal-and-default subtypes ship in the tree
        (`sale.order`, `event.track`, `helpdesk.ticket`, ...), so all this needs
        is a share user holding write access, which portal sharing grants.
        """
        internal_subtype = (
            self.env["mail.message.subtype"]
            .sudo()
            .create(
                {
                    "default": True,
                    "internal": True,
                    "name": "Internal Default",
                    "res_model": "mail.test.simple",
                }
            )
        )
        # portal sharing hands share users write access on shared records
        self.env["ir.model.access"].sudo().create(
            {
                "group_id": self.env.ref("base.group_portal").id,
                "model_id": self.env["ir.model"]._get("mail.test.simple").id,
                "name": "portal write on mail.test.simple",
                "perm_create": False,
                "perm_read": True,
                "perm_unlink": False,
                "perm_write": True,
            }
        )
        subscribed = self.partner_employee

        got = {}
        for label, user in (
            ("employee", self.user_employee),
            ("portal", self.user_portal),
        ):
            document = (
                self.env["mail.test.simple"].sudo().create({"name": f"Doc {label}"})
            )
            document.with_user(user).message_subscribe(partner_ids=subscribed.ids)
            follower = (
                self.env["mail.followers"]
                .sudo()
                .search(
                    [
                        ("res_model", "=", "mail.test.simple"),
                        ("res_id", "=", document.id),
                        ("partner_id", "=", subscribed.id),
                    ]
                )
            )
            got[label] = follower.subtype_ids

        self.assertIn(
            internal_subtype,
            got["employee"],
            "precondition: an internal partner gets the internal default subtype",
        )
        self.assertEqual(
            got["portal"],
            got["employee"],
            "who subscribes must not change what the subscribed partner follows",
        )

    def test_followers_subtypes_self_subscribe_share(self):
        """A share user subscribing themselves is a customer too.

        `message_subscribe` short-circuited the customer lookup to `[]` when the
        only partner was the caller's own, which hands a portal user the
        internal default subtypes. Nothing caught it because the `internal`
        record rule on `mail.message.subtype` hid them from the portal user's
        own search -- and `sudo()` lifts that rule, which is exactly how
        `website_event_track`, `website_forum` and `website_mail` subscribe a
        visitor to the document they are looking at.
        """
        document = self.env["mail.test.simple"].browse(self.test_record.id)
        portal_partner = self.user_portal.partner_id
        self.assertTrue(portal_partner.partner_share)

        document.with_user(self.user_portal).sudo().message_subscribe(
            partner_ids=portal_partner.ids
        )

        follower = (
            self.env["mail.followers"]
            .sudo()
            .search(
                [
                    ("res_model", "=", "mail.test.simple"),
                    ("res_id", "=", document.id),
                    ("partner_id", "=", portal_partner.id),
                ]
            )
        )
        self.assertEqual(follower.subtype_ids, self.default_group_subtypes_portal)
        self.assertNotIn(self.mt_mg_def_int, follower.subtype_ids)

    @users("employee")
    @mute_logger("odoo.models.unlink")
    def test_followers_inverse_message_partner(self):
        test_record = self.test_record.with_env(self.env)
        partner0, partner1, partner2, partner3 = self.env["res.partner"].create(
            [
                {"email": f"partner.{n}@test.lan", "name": f"partner{n}"}
                for n in range(4)
            ]
        )
        self.assertFalse(test_record.message_follower_ids)
        self.assertFalse(test_record.message_partner_ids)

        # fillup with API
        test_record.message_subscribe(partner_ids=partner3.ids)
        self.assertEqual(test_record.message_follower_ids.partner_id, partner3)
        # set empty
        test_record.message_partner_ids = None
        self.assertFalse(test_record.message_follower_ids.partner_id)
        # set 1
        test_record.message_partner_ids = partner0
        self.assertEqual(test_record.message_follower_ids.partner_id, partner0)
        # set multiple when non-empty
        test_record.message_partner_ids = partner1 + partner2
        self.assertEqual(
            test_record.message_follower_ids.partner_id, partner1 + partner2
        )
        # remove 1
        test_record.message_partner_ids -= partner1
        self.assertEqual(test_record.message_follower_ids.partner_id, partner2)
        # add multiple with one already set
        test_record.message_partner_ids += partner1 + partner2
        self.assertEqual(
            test_record.message_follower_ids.partner_id, partner1 + partner2
        )
        # remove outside of existing
        test_record.message_partner_ids -= partner3
        self.assertEqual(
            test_record.message_follower_ids.partner_id, partner1 + partner2
        )
        # reset
        test_record.message_partner_ids = False
        self.assertFalse(test_record.message_follower_ids.partner_id)

        # test with inactive and commands
        partner0.write({"active": False})
        test_record.write({"message_partner_ids": [(4, partner0.id), (4, partner1.id)]})
        self.assertEqual(test_record.message_follower_ids.partner_id, partner1)

        # Test when the method inverse is called in batch
        other_record = test_record.create(
            {
                "name": "Other",
            }
        )
        records = test_record + other_record

        records.message_partner_ids = partner2 + partner3
        self.assertEqual(records.message_partner_ids, partner2 + partner3)

        records.message_partner_ids -= partner2
        self.assertEqual(records.message_partner_ids, partner3)

    @mute_logger("odoo.addons.base.models.ir_model", "odoo.models")
    def test_followers_inverse_message_partner_access_rights(self):
        """Make sure we're not bypassing security checks by setting a partner
        instead of a follower"""
        test_record = self.test_record.with_user(self.user_portal)
        partner0 = self.env["res.partner"].create(
            {
                "email": "partner1@test.lan",
                "name": "partner1",
            }
        )
        _name = test_record.name  # check portal user can read

        # set empty
        with self.assertRaises(AccessError):
            test_record.message_partner_ids = None
        # set 1
        with self.assertRaises(AccessError):
            test_record.message_partner_ids = partner0
        # remove 1
        with self.assertRaises(AccessError):
            test_record.message_partner_ids -= partner0

    @users("employee")
    def test_followers_private_address(self):
        """Test standard API does subscribe IDs the user can't read"""
        other_company = self.env["res.company"].sudo().create({"name": "Other Company"})
        private_address = self.env["res.partner"].create(
            {
                "name": "Private Address",
                "company_id": other_company.id,
            }
        )
        self.env.user.write({"company_ids": [(3, other_company.id)]})
        document = self.env["mail.test.simple"].browse(self.test_record.id)
        document.message_subscribe(
            partner_ids=(self.partner_portal | private_address).ids
        )
        self.assertEqual(
            document.message_follower_ids.partner_id,
            self.partner_portal | private_address,
        )

        # works through low-level API
        document._message_subscribe(
            partner_ids=(self.partner_portal | private_address).ids
        )
        self.assertEqual(
            document.message_follower_ids.partner_id,
            self.partner_portal | private_address,
        )

    @users("employee")
    def test_create_multi_followers(self):
        documents = self.env["mail.test.simple"].create([{"name": "ninja"}] * 5)
        for document in documents:
            self.assertEqual(
                document.message_follower_ids.partner_id, self.env.user.partner_id
            )
            self.assertEqual(
                document.message_follower_ids.subtype_ids, self.default_group_subtypes
            )

    def test_add_followers_and_multi_are_the_two_ways_in(self):
        """`_add_followers` applies the model's defaults; the map goes to `_multi`.

        `_add_followers` used to take `partner_ids` *and* an optional
        `subtypes` map that had to cover exactly those partners -- one argument
        derived from the other, with a `ValueError` standing in for a state the
        signature could have made unrepresentable. Callers that know the
        subtypes now say so by calling `_add_followers_multi` directly.
        """
        Followers = self.env["mail.followers"]
        document = self.env["mail.test.simple"].create({"name": "TwoWays"})
        partners = self.partner_employee + self.partner_admin

        Followers._add_followers(document._name, document.ids, partners.ids)
        self.env.flush_all()
        self.assertEqual(document.message_partner_ids, partners)
        self.assertEqual(
            document.message_follower_ids.subtype_ids, self.default_group_subtypes
        )

        wanted = self.env["mail.message.subtype"].sudo().search([], limit=1)
        Followers._add_followers_multi(
            document._name,
            {document.id: dict.fromkeys(partners.ids, wanted.ids)},
            existing_policy="replace",
        )
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(document.message_follower_ids.subtype_ids, wanted)

    def test_prepare_followers_vals_writes_nothing(self):
        """`_prepare_followers_vals` decides; `_add_followers_multi` writes.

        The `force` policy used to `unlink()` from inside the "prepare" method,
        so the name lied and the function could not be called speculatively. It
        was then reported back as `obsolete_ids` instead, and is now gone
        entirely -- `replace` reaches the same end state without destroying and
        re-creating the row, and `force` alone read the dense
        `res_ids x partner_ids` product back out of a sparse request.
        """
        Followers = self.env["mail.followers"]
        document = self.env["mail.test.simple"].create({"name": "Pure"})
        document.message_subscribe(partner_ids=self.partner_employee.ids)
        existing = Followers.sudo().search(
            [("res_model", "=", document._name), ("res_id", "=", document.id)]
        )
        self.assertTrue(existing)
        wanted = self.env["mail.message.subtype"].sudo().search([], limit=1)

        new_vals, updates = Followers._prepare_followers_vals(
            document._name,
            {document.id: {self.partner_employee.id: wanted.ids}},
            check_existing=True,
            existing_policy="replace",
        )
        self.assertFalse(new_vals, "the follower exists, nothing to create")
        self.assertEqual(list(updates), existing.ids, "the update is reported...")
        self.env.invalidate_all()
        self.assertEqual(
            existing.subtype_ids,
            self.default_group_subtypes,
            "...and not performed",
        )

    def test_add_followers_multi_reapplies_policy_after_a_race(self):
        """A row created behind our back must still get the requested subtypes.

        The unique constraint is what serialises two sessions subscribing the
        same partner to the same record. Swallowing the resulting
        `UniqueViolation` is right for `skip` and wrong for `replace`/`update`,
        whose subtypes would silently stay whatever the winner wrote.
        `check_existing=False` models the race exactly: the row exists, and was
        invisible when the vals were prepared.
        """
        Followers = self.env["mail.followers"]
        document = self.env["mail.test.simple"].create({"name": "Race"})
        wanted, other = self.env["mail.message.subtype"].sudo().search([], limit=2)
        Followers.sudo().create(
            {
                "partner_id": self.partner_employee.id,
                "res_id": document.id,
                "res_model": document._name,
                "subtype_ids": [Command.set(other.ids)],
            }
        ).flush_recordset()

        Followers._add_followers_multi(
            document._name,
            {document.id: {self.partner_employee.id: wanted.ids}},
            check_existing=False,
            existing_policy="replace",
        )
        follower = Followers.sudo().search(
            [
                ("res_model", "=", document._name),
                ("res_id", "=", document.id),
                ("partner_id", "=", self.partner_employee.id),
            ]
        )
        self.assertEqual(
            follower.subtype_ids, wanted, "the race did not eat the replace"
        )

    def test_no_policy_touches_a_pair_the_caller_did_not_name(self):
        """`subtypes_per_record` is sparse; nothing may read it as dense.

        The obsolete-row query asks for `res_ids x partner_ids` because that is
        one query instead of many. `force` deleted everything it returned and
        re-created only the sparse pairs, so a partner following one record of a
        batch was unsubscribed from it by a call that named them for a different
        record. The policy is gone; this pins that no survivor grew the habit.
        """
        Followers = self.env["mail.followers"].sudo()
        d1, d2 = self.env["mail.test.simple"].create([{"name": "F1"}, {"name": "F2"}])
        p1, p2 = self.partner_employee, self.partner_admin
        sids = self.default_group_subtypes.ids
        Followers._add_followers_multi(
            d1._name, {d1.id: {p1.id: sids, p2.id: sids}, d2.id: {p2.id: sids}}
        )
        self.env.flush_all()

        for policy in ("skip", "replace", "update"):
            with self.subTest(policy=policy):
                Followers._add_followers_multi(
                    d1._name,
                    {d1.id: {p1.id: sids}, d2.id: {p2.id: sids}},
                    existing_policy=policy,
                )
                self.env.flush_all()
                self.env.invalidate_all()
                self.assertEqual(
                    sorted(
                        (fol.res_id, fol.partner_id.id)
                        for fol in Followers.search(
                            [
                                ("res_model", "=", d1._name),
                                ("res_id", "in", (d1 + d2).ids),
                            ]
                        )
                    ),
                    sorted([(d1.id, p1.id), (d1.id, p2.id), (d2.id, p2.id)]),
                    "(d1, p2) was never named by the caller and must survive",
                )

    def test_skipping_followers_does_not_rewrite_the_message_type(self):
        """notify_skip_followers is about followers, not about the channel.

        It used to be expressed by overwriting message_type with
        user_notification, which is the sentinel _get_recipient_data
        reads to exclude followers -- and also the value sms reads to pick
        the delivery channel. The flag silently downgraded an SMS to an email.
        """
        Followers = self.env["mail.followers"]
        document = self.env["mail.test.simple"].create({"name": "Skip"})
        document.message_subscribe(partner_ids=self.partner_employee.ids)
        self.env.flush_all()
        subtype_id = self.env.ref("mail.mt_comment").id

        with_followers = Followers._get_recipient_data(
            document, "comment", subtype_id, []
        )[document.id]
        self.assertIn(self.partner_employee.id, with_followers, "precondition")

        without = Followers._get_recipient_data(
            document, "comment", subtype_id, [], include_followers=False
        )[document.id]
        self.assertFalse(without, "the flag drops followers...")

        named = Followers._get_recipient_data(
            document,
            "comment",
            subtype_id,
            self.partner_admin.ids,
            include_followers=False,
        )[document.id]
        self.assertEqual(
            set(named),
            {self.partner_admin.id},
            "...and keeps the explicitly named recipients",
        )

    def test_follower_without_document_cannot_be_duplicated(self):
        """`res_id` is nullable and plain UNIQUE counts NULLs as distinct.

        Without `NULLS NOT DISTINCT` the constraint let a partner follow the
        same model twice with no document at all -- a pair of rows no code knows
        how to read.
        """
        Followers = self.env["mail.followers"].sudo()
        vals = {"res_model": "mail.test.simple", "partner_id": self.partner_admin.id}
        Followers.create(vals).flush_recordset()
        with self.assertRaises(IntegrityError), mute_logger("odoo.db.cursor"):
            Followers.create(dict(vals)).flush_recordset()

    def test_recipient_is_follower_is_not_a_lie_for_share_partners(self):
        """A share partner who follows the record follows it, internal subtype or not.

        The `internal` test used to sit in the JOIN, which dropped a share
        partner's follower row outright. When that partner was *also* an
        explicit recipient the `UNION ALL` branch put them back with a
        hardcoded `is_follower = FALSE` -- so a partner who demonstrably
        follows the record was reported as not following it. What the internal
        subtype must prevent is *notifying them through following*, and that is
        unchanged: with no explicit recipients they do not appear at all.
        """
        Followers = self.env["mail.followers"]
        internal_subtype = self.env.ref("mail.mt_note")
        self.assertTrue(internal_subtype.internal, "precondition")
        self.assertTrue(self.partner_portal.partner_share, "precondition")

        document = self.env["mail.test.simple"].create({"name": "Internal"})
        document.message_subscribe(
            partner_ids=(self.partner_portal | self.partner_employee).ids
        )
        Followers.sudo().search(
            [("res_model", "=", document._name), ("res_id", "=", document.id)]
        ).subtype_ids = [Command.set(internal_subtype.ids)]
        self.env.flush_all()

        without_pids = Followers._get_recipient_data(
            document, "comment", internal_subtype.id, []
        )[document.id]
        self.assertNotIn(
            self.partner_portal.id,
            without_pids,
            "an internal subtype still does not notify a share follower",
        )

        with_pids = Followers._get_recipient_data(
            document, "comment", internal_subtype.id, self.partner_portal.ids
        )[document.id]
        self.assertTrue(
            with_pids[self.partner_portal.id]["is_follower"],
            "named as a recipient, the share partner keeps the truth about following",
        )

    def test_document_invalidation_on_unlink_and_move(self):
        """Deleting or moving a follower row invalidates both documents."""
        source = self.env["mail.test.simple"].create({"name": "Source"})
        target = self.env["mail.test.simple"].create({"name": "Target"})
        source.message_subscribe(partner_ids=self.partner_employee.ids)
        self.assertEqual(source.message_partner_ids, self.partner_employee)

        follower = source.message_follower_ids.sudo()
        follower.write({"res_id": target.id})
        self.assertFalse(source.message_partner_ids, "the old document lost it")
        self.assertEqual(
            target.message_partner_ids, self.partner_employee, "the new one gained it"
        )

        follower.unlink()
        self.assertFalse(target.message_partner_ids, "unlink invalidates too")

    @users("employee")
    def test_subscriptions_data_fetch(self):
        """Test that _get_subscription_data gives correct values when modifying followers manually."""
        test_record = self.test_record
        test_record_copy = self.test_record.copy()
        test_records = test_record + test_record_copy
        test_record.message_subscribe([self.user_employee.partner_id.id])
        subscription_data = self.env["mail.followers"]._get_subscription_data(
            [(test_records._name, test_records.ids)], None
        )
        self.assertEqual(len(subscription_data), 1)
        row = subscription_data[0]
        self.assertEqual(row.res_model, test_records._name)
        self.assertEqual(row.res_id, test_record.id)
        self.assertEqual(row.partner_id, self.user_employee.partner_id.id)
        self.assertEqual(
            sorted(row.subtype_ids), sorted(self.default_group_subtypes.ids)
        )
        self.assertFalse(row.partner_share)
        self.assertTrue(row.partner_active)

        # a NamedTuple, so the positional contract three call sites relied on is
        # unchanged: unpacking, indexing and slicing all still work
        fol_id, res_model, res_id, partner_id, subtype_ids, pshare, active = row
        self.assertEqual(
            (fol_id, res_model, res_id), (row.id, row.res_model, row.res_id)
        )
        self.assertEqual(
            (partner_id, subtype_ids, pshare, active),
            (row.partner_id, row.subtype_ids, row.partner_share, row.partner_active),
        )
        self.assertEqual(row[3:], (row.partner_id, row.subtype_ids, pshare, active))
        self.assertEqual(len(row), 7)

        self.env["mail.followers"].browse(fol_id).sudo().res_id = test_record_copy
        subscription_data = self.env["mail.followers"]._get_subscription_data(
            [(test_records._name, test_records.ids)], None
        )
        self.assertEqual(len(subscription_data), 1)
        self.assertEqual(subscription_data[0].res_id, test_record_copy.id)

    @users("employee")
    def test_subscriptions_data_fetch_edge_cases(self):
        """Empty inputs must be answered without touching the database, and a
        follower with no subtype must report an empty list -- not ``[None]``,
        which used to reach the ORM as ``Command.unlink(None)``."""
        Followers = self.env["mail.followers"]
        test_record = self.test_record
        test_record.message_subscribe([self.user_employee.partner_id.id])
        fol = test_record.message_follower_ids.sudo()
        fol.subtype_ids = [(5, 0, 0)]
        fol.flush_recordset()

        with self.assertQueryCount(employee=0):
            self.assertEqual(Followers._get_subscription_data([], None), [])
            # 'partner_id' is required: an explicitly empty filter matches nothing
            self.assertEqual(
                Followers._get_subscription_data(
                    [(test_record._name, test_record.ids)], []
                ),
                [],
            )

        data = Followers._get_subscription_data(
            [(test_record._name, test_record.ids)], None
        )
        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0].subtype_ids, [], "a subtype-less follower reports no subtype"
        )

    def test_followers_expose_no_partner_prose(self):
        """``mail.followers`` is readable by every internal user and carries no
        record rule, so a ``related`` field on it answers in sudo for partners the
        partner ACL denies. Only the flag the client renders may do that."""
        Followers = self.env["mail.followers"]
        for fname in ("name", "email"):
            self.assertNotIn(
                fname,
                Followers._fields,
                "a related field here discloses partner %s to any internal user, "
                "and nothing reads it -- the client uses partner_id.name" % fname,
            )
        self.assertNotIn("email", Followers._to_store_defaults(None))
        self.assertNotIn("name", Followers._to_store_defaults(None))

        other_company = (
            self.env["res.company"].sudo().create({"name": "Followers Audit Co"})
        )
        secret = (
            self.env["res.partner"]
            .sudo()
            .create(
                {
                    "name": "Followers Audit Secret",
                    "email": "secret@audit.example",
                    "company_id": other_company.id,
                }
            )
        )
        self.test_record.message_subscribe(secret.ids)
        self.env.flush_all()

        employee = self.user_employee
        self.assertFalse(
            self.env["res.partner"]
            .with_user(employee)
            .search([("id", "=", secret.id)]),
            "precondition: the partner itself is out of reach for this user",
        )
        rows = Followers.with_user(employee).search_read(
            [("partner_id", "=", secret.id)], ["partner_id"]
        )
        self.assertTrue(rows, "the follower row itself stays readable, as upstream")
        self.assertFalse(
            rows[0]["partner_id"], "and the partner is blanked by its own ACL"
        )


@tagged("mail_followers")
@tagged("mail_followers", "security")
class FollowerAccessTest(MailCommon):
    """Who follows a document is part of the document.

    `mail.followers` grants `read` to every internal user and carries no record
    rule, so the follower rows of a record the caller is denied were legible
    while the record and its messages were not. Three entry points reached them
    and not one of them checked: the ORM directly, `message_get_followers`
    (`@api.readonly`, so `call_kw` on any id), and `_thread_to_store`.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.secret_partner = cls.env["res.partner"].create(
            {"name": "Confidential Contact", "email": "confidential@test.example"}
        )
        # `access='admin'` is what ir_rule_mail_test_access_internal excludes
        cls.denied = cls.env["mail.test.access"].create(
            {"name": "Denied", "access": "admin"}
        )
        cls.allowed = cls.env["mail.test.access"].create(
            {"name": "Allowed", "access": "public"}
        )
        (cls.denied + cls.allowed).message_subscribe(partner_ids=cls.secret_partner.ids)
        cls.env.flush_all()

    def _denied_follower(self):
        return (
            self.env["mail.followers"]
            .sudo()
            .search(
                [
                    ("res_model", "=", self.denied._name),
                    ("res_id", "=", self.denied.id),
                    ("partner_id", "=", self.secret_partner.id),
                ]
            )
        )

    @users("employee")
    def test_every_read_surface_refuses_a_denied_document(self):
        """`search` filters; `read_group` and `search_count` are built on it.

        `read_group` alone was enough: grouping by `partner_id` over all
        followers named every partner following anything, and grouping by
        `res_id` counted them per record.
        """
        Followers = self.env["mail.followers"]
        secret_id = self._denied_follower().id
        with self.assertRaises(AccessError, msg="precondition: the record is denied"):
            self.denied.with_env(self.env).read(["name"])

        self.assertNotIn(
            secret_id,
            Followers.search([("res_model", "=", self.denied._name)]).ids,
            "search",
        )
        self.assertEqual(
            Followers.search_count([("id", "=", secret_id)]), 0, "search_count"
        )
        self.assertFalse(
            Followers._read_group([("res_id", "=", self.denied.id)], ["partner_id"]),
            "read_group by partner_id named a follower of a denied record",
        )
        self.assertNotIn(
            self.denied.id,
            [
                group[0]
                for group in Followers._read_group(
                    [("res_model", "=", self.denied._name)], ["res_id"]
                )
            ],
            "read_group by res_id counted a denied record",
        )
        with self.assertRaises(AccessError, msg="a direct read is not a way around"):
            Followers.browse(secret_id).read(["partner_id"])

    @users("employee")
    def test_the_readable_document_still_answers(self):
        """The filter is about the document, not about followers in general."""
        Followers = self.env["mail.followers"]
        allowed = Followers.search(
            [("res_model", "=", self.allowed._name), ("res_id", "=", self.allowed.id)]
        )
        self.assertIn(self.secret_partner, allowed.partner_id)
        self.assertEqual(
            self.allowed.with_env(self.env).message_partner_ids,
            allowed.partner_id,
            "the one2many on a readable record is unchanged",
        )

    @users("employee")
    def test_own_subscription_is_readable_on_a_denied_document(self):
        """You must be able to see -- and so unfollow -- what you follow.

        Reading your own row is the one case that does not ask about the
        document, because the answer would deny you the only handle you have.
        """
        own = (
            self.env["mail.followers"]
            .sudo()
            .create(
                {
                    "res_model": self.denied._name,
                    "res_id": self.denied.id,
                    "partner_id": self.env.user.partner_id.id,
                }
            )
        )
        self.env.flush_all()
        Followers = self.env["mail.followers"]
        self.assertEqual(
            Followers.browse(own.id).read(["res_id"])[0]["res_id"], self.denied.id
        )
        self.assertIn(own.id, Followers.search([("res_id", "=", self.denied.id)]).ids)

    @users("employee")
    def test_message_get_followers_checks_the_document(self):
        """It is `@api.readonly` and reachable through `call_kw` on any id."""
        with self.assertRaises(AccessError):
            self.denied.with_env(self.env).message_get_followers()
        self.assertTrue(self.allowed.with_env(self.env).message_get_followers())

    @users("employee")
    def test_thread_to_store_checks_the_document(self):
        """The same guard, reached through `Store` rather than through call_kw."""
        with self.assertRaises(AccessError):
            self.denied.with_env(self.env)._thread_to_store(
                Store(), [], request_list=["followers"]
            )
        store = Store()
        self.allowed.with_env(self.env)._thread_to_store(
            store, [], request_list=["followers"]
        )
        self.assertIn("Confidential Contact", str(store.get_result()))

    def test_the_batch_follower_reader_agrees_with_the_single_one(self):
        """The paged reader must flush what its raw SQL reads.

        `_message_followers_to_store_batch` wraps an ORM `query.select()` and ran
        it through `env.cr.execute`, which bypasses `Environment.flush_query` and
        discards the `to_flush` the subquery carries for `res_model`, `res_id`
        and `partner_id`. `mail.followers.res_model` is a field this ORM defers,
        so a pending write to it left the batch reader answering from rows the
        transaction had already moved -- while `_message_followers_to_store`, an
        ORM search and therefore flushed, answered correctly about the same
        record at the same instant.

        The single-record reader now routes through the paged one, so the two
        cannot disagree any more; what keeps this test honest is the final
        assertion that the moved follower is absent, which a raw, unflushed
        read would fail.
        """
        record = self.env["mail.test.simple"].create({"name": "Two readers"})
        partner = self.env["res.partner"].create(
            {"name": "Mover", "email": "mover@test.example"}
        )
        record.message_subscribe(partner_ids=partner.ids)
        self.env.flush_all()
        self.env.invalidate_all()

        follower = (
            self.env["mail.followers"]
            .sudo()
            .search(
                [
                    ("res_model", "=", record._name),
                    ("res_id", "=", record.id),
                    ("partner_id", "=", partner.id),
                ]
            )
        )
        self.assertTrue(follower)
        # deferred, not yet in the table the raw query reads
        follower.write({"res_model": "res.partner"})

        batched = record._message_followers_to_store_batch(Store())
        single = record._message_followers_to_store(Store())
        self.assertEqual(
            batched.get(record.id, self.env["mail.followers"]).ids,
            single.ids,
            "the paged reader must see the same followers as the single-record one",
        )
        self.assertFalse(
            single, "precondition: the follower no longer belongs to this record"
        )

    def test_message_get_followers_pages_after_the_given_follower(self):
        """`message_get_followers(after=X)` is the "load more" call: it must
        return the page after X only, and add it to what the client holds
        rather than replace it."""
        record = self.env["mail.test.simple"].create({"name": "Paged"})
        partners = self.env["res.partner"].create(
            [{"name": f"Follower {index}"} for index in range(3)]
        )
        record.message_subscribe(partner_ids=partners.ids)
        self.env.flush_all()
        followers = (
            self.env["mail.followers"]
            .sudo()
            .search(
                [
                    ("res_model", "=", record._name),
                    ("res_id", "=", record.id),
                    ("partner_id", "in", partners.ids),
                ],
                order="id ASC",
            )
        )
        self.assertEqual(len(followers), 3)

        store = Store()
        page = record._message_followers_to_store(store, after=followers[0].id, limit=1)
        self.assertEqual(page, followers[1])
        result = store.get_result()
        self.assertEqual(
            [follower["id"] for follower in result["mail.followers"]],
            [followers[1].id],
        )
        [thread] = result["mixin.mail.thread"]
        [(mode, _ids)] = thread["followers"]
        self.assertEqual(mode, "ADD", "a continuation page adds to the client's list")

        first_page = Store()
        record._message_followers_to_store(first_page, limit=2)
        result = first_page.get_result()
        self.assertEqual(
            [follower["id"] for follower in result["mail.followers"]],
            followers[:2].ids,
        )
        [thread] = result["mixin.mail.thread"]
        self.assertEqual(
            len(thread["followers"]),
            2,
            "a first page replaces the client's list: plain entries, no ADD wrapper",
        )


class AdvancedFollowersTest(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_portal_user()

        cls.test_track = (
            cls.env["mail.test.track"]
            .with_user(cls.user_employee)
            .create(
                {
                    "name": "Test",
                }
            )
        )

        Subtype = cls.env["mail.message.subtype"]

        # clean demo data to avoid interferences
        Subtype.search(
            [("res_model", "in", ["mail.test.container", "mail.test.track"])]
        ).unlink()

        # mail.test.track subtypes (aka: task records)
        cls.sub_track_1 = Subtype.create(
            {
                "name": "Track (with child relation) 1",
                "default": False,
                "res_model": "mail.test.track",
            }
        )
        cls.sub_track_2 = Subtype.create(
            {
                "name": "Track (with child relation) 2",
                "default": False,
                "res_model": "mail.test.track",
            }
        )
        cls.sub_track_nodef = Subtype.create(
            {
                "name": "Generic Track subtype",
                "default": False,
                "internal": False,
                "res_model": "mail.test.track",
            }
        )
        cls.sub_track_def = Subtype.create(
            {
                "name": "Default track subtype",
                "default": True,
                "internal": False,
                "res_model": "mail.test.track",
            }
        )
        cls.sub_track_parent_def = Subtype.create(
            {
                "name": "Parent track subtype",
                "default": False,
                "res_model": "mail.test.track",
                "parent_id": cls.sub_track_def.id,
                "relation_field": "parent_id",
            }
        )

        # mail.test.container subtypes (aka: project records)
        cls.umb_nodef = Subtype.create(
            {
                "name": "Container NoDefault",
                "default": False,
                "res_model": "mail.test.container",
            }
        )
        cls.umb_def = Subtype.create(
            {
                "name": "Container Default",
                "default": True,
                "res_model": "mail.test.container",
            }
        )
        cls.umb_def_int = Subtype.create(
            {
                "name": "Container Default",
                "default": True,
                "internal": True,
                "res_model": "mail.test.container",
            }
        )
        # -> subtypes for auto subscription from container to sub records
        cls.umb_autosub_def = Subtype.create(
            {
                "name": "Container AutoSub (default)",
                "default": True,
                "res_model": "mail.test.container",
                "parent_id": cls.sub_track_1.id,
                "relation_field": "container_id",
            }
        )
        cls.umb_autosub_nodef = Subtype.create(
            {
                "name": "Container AutoSub 2",
                "default": False,
                "res_model": "mail.test.container",
                "parent_id": cls.sub_track_2.id,
                "relation_field": "container_id",
            }
        )

        # generic subtypes
        cls.sub_comment = cls.env.ref("mail.mt_comment")
        cls.sub_generic_int_nodef = Subtype.create(
            {
                "name": "Generic internal subtype",
                "default": False,
                "internal": True,
            }
        )
        cls.sub_generic_int_def = Subtype.create(
            {
                "name": "Generic internal subtype (default)",
                "default": True,
                "internal": True,
            }
        )

    def test_auto_subscribe_create(self):
        """Creator of records are automatically added as followers"""
        for user, should_subscribe in [
            (self.user_root, False),
            (self.user_employee, True),
            (self.user_portal, False),
        ]:
            with self.subTest(user_name=user.name):
                # sudo, as done through mailgateway for example
                if user == self.user_portal:
                    new_rec = (
                        self.env["mail.test.track"].with_user(user).sudo().create({})
                    )
                else:
                    new_rec = self.env["mail.test.track"].with_user(user).create({})
                self.assertEqual(
                    new_rec.message_partner_ids,
                    user.partner_id if should_subscribe else self.env["res.partner"],
                )

    @mute_logger("odoo.models.unlink")
    def test_auto_subscribe_inactive(self):
        """Test inactive are not added as followers in automated subscription"""
        # `base.user_admin` holds the only active `base.group_system` seat on a
        # `-i mail` database (`base.user_root` carries the group but is inactive),
        # and `_check_at_least_one_administrator` refuses to let it go. Seat a
        # second administrator so the deactivation under test is allowed at all;
        # the subject here is follower subscription, not the admin invariant.
        self.env["res.users"].create(
            {
                "login": "second_admin_for_deactivation",
                "name": "Second Administrator",
                "group_ids": [(4, self.env.ref("base.group_system").id)],
            }
        )
        self.test_track.user_id = False
        self.user_admin.active = False
        self.user_admin.flush_recordset()
        self.partner_admin.active = False
        self.partner_admin.flush_recordset()

        self.test_track.with_user(self.user_admin).message_post(
            body="Coucou hibou", message_type="comment"
        )
        self.assertEqual(
            self.test_track.message_partner_ids, self.user_employee.partner_id
        )
        self.assertEqual(
            self.test_track.message_follower_ids.partner_id,
            self.user_employee.partner_id,
        )

        self.test_track.write({"user_id": self.user_admin.id})
        self.assertEqual(
            self.test_track.message_partner_ids, self.user_employee.partner_id
        )
        self.assertEqual(
            self.test_track.message_follower_ids.partner_id,
            self.user_employee.partner_id,
        )

        new_record = (
            self.env["mail.test.track"]
            .with_user(self.user_admin)
            .create(
                {
                    "name": "Test",
                }
            )
        )
        self.assertFalse(
            new_record.message_partner_ids, "Filters out inactive partners"
        )
        self.assertFalse(
            new_record.message_follower_ids.partner_id,
            "Does not subscribe inactive partner",
        )

    def test_auto_subscribe_post(self):
        """People posting a discussion message are automatically added as
        followers"""
        record = self.test_track.with_user(self.user_admin)
        for message_type, subtype, should_subscribe in [
            ("comment", self.env.ref("mail.mt_note"), False),
            ("comment", self.env.ref("mail.mt_comment"), True),
            ("email_outgoing", self.env.ref("mail.mt_note"), False),
            ("email_outgoing", self.env.ref("mail.mt_comment"), True),
            ("notification", self.env.ref("mail.mt_comment"), False),
        ]:
            with self.subTest(message_type=message_type, subtype_name=subtype.name):
                record.message_unsubscribe(partner_ids=self.user_admin.partner_id.ids)
                record.message_post(
                    body=f"Posting with {message_type} {subtype.name}",
                    message_type=message_type,
                    subtype_id=subtype.id,
                )
                if should_subscribe:
                    self.assertIn(
                        self.user_admin.partner_id, record.message_partner_ids
                    )
                else:
                    self.assertNotIn(
                        self.user_admin.partner_id, record.message_partner_ids
                    )

    def test_auto_subscribe_responsible(self):
        """Responsibles are tracked and added as followers"""
        sub = (
            self.env["mail.test.track"]
            .with_user(self.user_employee)
            .create(
                {
                    "name": "Test",
                    "user_id": self.user_admin.id,
                }
            )
        )
        self.assertEqual(
            sub.message_partner_ids,
            (self.user_employee.partner_id | self.user_admin.partner_id),
        )

        # After unsubscribing, current user should not appear in suggested recipients
        sub.message_unsubscribe(partner_ids=self.user_admin.partner_id.ids)
        suggested = sub.with_user(self.user_admin)._message_get_suggested_recipients()
        suggested_partner_ids = [
            r["partner_id"] for r in suggested if r.get("partner_id")
        ]
        self.assertNotIn(
            self.user_admin.partner_id.id,
            suggested_partner_ids,
            "Current user should not appear in suggested recipients after unsubscribing",
        )

    @mute_logger("odoo.models.unlink")
    def test_auto_subscribe_defaults(self):
        """Test auto subscription based on an container record. This mimics
        the behavior of addons like project and task where subscribing to
        some project's subtypes automatically subscribe the follower to its tasks.

        Functional rules applied here

         * subscribing to an container subtype with parent_id / relation_field set
           automatically create subscription with matching subtypes
         * subscribing to a sub-record as creator applies default subtype values
         * portal user should not have access to internal subtypes

        Inactive partners should not be auto subscribed.
        """
        container = (
            self.env["mail.test.container"]
            .with_context(self._test_context)
            .create(
                {
                    "name": "Project-Like",
                }
            )
        )

        # have an inactive partner to check auto subscribe does not subscribe it
        user_root = self.env.ref("base.user_root")
        self.assertFalse(user_root.active)
        self.assertFalse(user_root.partner_id.active)

        container.message_subscribe(
            partner_ids=(self.partner_portal | user_root.partner_id).ids
        )
        container.message_subscribe(
            partner_ids=self.partner_admin.ids,
            subtype_ids=(
                self.sub_comment | self.umb_autosub_nodef | self.sub_generic_int_nodef
            ).ids,
        )
        self.assertEqual(
            container.message_partner_ids, self.partner_portal | self.partner_admin
        )
        follower_por = container.message_follower_ids.filtered(
            lambda f: f.partner_id == self.partner_portal
        )
        follower_adm = container.message_follower_ids.filtered(
            lambda f: f.partner_id == self.partner_admin
        )
        self.assertEqual(
            follower_por.subtype_ids,
            self.sub_comment | self.umb_def | self.umb_autosub_def,
            "Subscribe: Default subtypes: comment (default generic) and two model-related defaults",
        )
        self.assertEqual(
            follower_adm.subtype_ids,
            self.sub_comment | self.umb_autosub_nodef | self.sub_generic_int_nodef,
            "Subscribe: Asked subtypes when subscribing",
        )

        sub1 = (
            self.env["mail.test.track"]
            .with_user(self.user_employee)
            .create(
                {
                    "name": "Task-Like Test",
                    "container_id": container.id,
                }
            )
        )

        self.assertEqual(
            sub1.message_partner_ids,
            self.partner_portal | self.partner_admin | self.user_employee.partner_id,
            "Followers: creator (employee) + auto subscribe from parent (portal)",
        )
        follower_por = sub1.message_follower_ids.filtered(
            lambda fol: fol.partner_id == self.partner_portal
        )
        follower_adm = sub1.message_follower_ids.filtered(
            lambda fol: fol.partner_id == self.partner_admin
        )
        follower_emp = sub1.message_follower_ids.filtered(
            lambda fol: fol.partner_id == self.user_employee.partner_id
        )
        self.assertEqual(
            follower_por.subtype_ids,
            self.sub_comment | self.sub_track_1,
            "AutoSubscribe: comment (generic checked), Track (with child relation) 1 as Umbrella AutoSub (default) was checked",
        )
        self.assertEqual(
            follower_adm.subtype_ids,
            self.sub_comment | self.sub_track_2 | self.sub_generic_int_nodef,
            "AutoSubscribe: comment (generic checked), Track (with child relation) 2) as Umbrella AutoSub 2 was checked, Generic internal subtype (generic checked)",
        )
        self.assertEqual(
            follower_emp.subtype_ids,
            self.sub_comment | self.sub_track_def | self.sub_generic_int_def,
            "AutoSubscribe: only default one as no subscription on parent",
        )

        # check portal generic subscribe
        sub1.message_unsubscribe(partner_ids=self.partner_portal.ids)
        sub1.message_subscribe(partner_ids=self.partner_portal.ids)
        follower_por = sub1.message_follower_ids.filtered(
            lambda fol: fol.partner_id == self.partner_portal
        )

        self.assertEqual(
            follower_por.subtype_ids,
            self.sub_comment | self.sub_track_def,
            "AutoSubscribe: only default one as no subscription on parent (no internal as portal)",
        )

        # check auto subscribe as creator + auto subscribe as parent follower takes both subtypes
        container.message_subscribe(
            partner_ids=self.user_employee.partner_id.ids,
            subtype_ids=(
                self.sub_comment | self.sub_generic_int_nodef | self.umb_autosub_nodef
            ).ids,
        )
        sub2 = (
            self.env["mail.test.track"]
            .with_user(self.user_employee)
            .create(
                {
                    "name": "Task-Like Test",
                    "container_id": container.id,
                }
            )
        )
        follower_emp = sub2.message_follower_ids.filtered(
            lambda fol: fol.partner_id == self.user_employee.partner_id
        )
        defaults = self.sub_comment | self.sub_track_def | self.sub_generic_int_def
        parents = self.sub_generic_int_nodef | self.sub_track_2
        self.assertEqual(
            follower_emp.subtype_ids,
            defaults + parents,
            "AutoSubscribe: at create auto subscribe as creator + from parent take both subtypes",
        )

        container.message_follower_ids = [Command.clear()]
        parent_track = (
            self.env["mail.test.track"]
            .with_user(self.user_employee)
            .create(
                {
                    "name": "Task-Like",
                    "container_id": container.id,
                }
            )
        )

        child_track = (
            self.env["mail.test.track"]
            .with_user(self.user_admin)
            .create(
                {
                    "name": "Task-Like Test-sub-task",
                    "parent_id": parent_track.id,
                    "container_id": container.id,
                }
            )
        )
        self.assertIn(
            self.user_employee.partner_id,
            child_track.message_follower_ids.partner_id,
            "The partner from the parent has not been added as follower.",
        )


@tagged("mail_followers")
class AdvancedResponsibleNotifiedTest(MailCommon):
    def setUp(self):
        super().setUp()

        # patch registry to simulate a ready environment so that _message_auto_subscribe_notify
        # will be executed with the associated notification
        old = self.env.registry.ready
        self.env.registry.ready = True
        self.addCleanup(setattr, self.env.registry, "ready", old)

    def test_auto_subscribe_notify_email(self):
        """Responsible is notified when assigned"""
        partner = self.env["res.partner"].create(
            {"name": "demo1", "email": "demo1@test.mycompany.com"}
        )
        notified_user = self.env["res.users"].create(
            {
                "login": "demo1",
                "partner_id": partner.id,
                "notification_type": "email",
            }
        )

        # TODO master: add a 'state' selection field on 'mail.test.track' with a 'done' value to have a complete test
        # check that 'default_state' context does not collide with mail.mail default values
        sub = (
            self.env["mail.test.track"]
            .with_user(self.user_employee)
            .with_context({"default_state": "done", "mail_notify_force_send": False})
            .create(
                {
                    "name": "Test",
                    "user_id": notified_user.id,
                }
            )
        )

        self.assertEqual(
            sub.message_partner_ids,
            (self.user_employee.partner_id | notified_user.partner_id),
        )
        # fetch created "You have been assigned to 'Test'" mail.message
        mail_message = self.env["mail.message"].search(
            [
                ("model", "=", "mail.test.track"),
                ("res_id", "=", sub.id),
                ("partner_ids", "in", partner.id),
            ]
        )
        self.assertEqual(1, len(mail_message))

        # verify that a mail.mail is attached to it with the correct state ('outgoing')
        mail_notification = mail_message.notification_ids
        self.assertEqual(1, len(mail_notification))
        self.assertTrue(bool(mail_notification.mail_mail_id))
        self.assertEqual(mail_notification.mail_mail_id.state, "outgoing")

    def _create_records_one_user_each(self, count, users):
        """Create `count` records, each assigned to a different user, and return
        the queries that cost plus the records."""
        vals = [
            {"name": f"Assigned {index}", "user_id": users[index].id}
            for index in range(count)
        ]
        self.env.flush_all()
        self.env.invalidate_all()
        before = self.cr.sql_statement_count
        records = (
            self.env["mail.test.track"]
            .with_user(self.user_employee)
            .with_context(mail_notify_force_send=False)
            .create(vals)
        )
        self.env.flush_all()
        return self.cr.sql_statement_count - before, records

    def test_assigning_a_batch_to_different_people_costs_one_batch(self):
        """Assigning N records to N *different* users must stay one notify batch.

        `_message_auto_subscribe_notify_batch` used to key its groups on the
        recipients as well as the template and the language, so distinct
        assignees -- the normal shape of a bulk assignment -- produced one group
        per record and `_message_notify_batch` paid every per-batch cost once per
        record. Measured at the time: 67 queries for twenty records sharing an
        assignee against 254 for twenty records with their own.

        Asserted as a **marginal** cost at N > 1, because that is the only scale
        at which this class of defect is visible: every `assertQueryCount` on
        this path measures a single record, where a batch that splits into
        batches of one costs exactly what a correct batch of one costs.
        """
        users = self.env["res.users"].create(
            [
                {
                    "email": f"assignee.{index}@test.example.com",
                    "login": f"assignee_{index}",
                    "name": f"Assignee {index}",
                    "notification_type": "email",
                }
                for index in range(20)
            ]
        )
        few_queries, _few = self._create_records_one_user_each(2, users)
        many_queries, many_records = self._create_records_one_user_each(20, users)
        self.assertLessEqual(
            many_queries - few_queries,
            30,
            f"18 further records, each with their own assignee, cost "
            f"{many_queries - few_queries} extra queries "
            f"(2 records: {few_queries}, 20 records: {many_queries})",
        )

        notifications = self.env["mail.message"].search(
            [
                ("model", "=", "mail.test.track"),
                ("res_id", "in", many_records.ids),
                ("message_type", "=", "user_notification"),
            ]
        )
        self.assertEqual(
            len(notifications), 20, "every record still gets its own notification"
        )
        self.assertEqual(
            [
                notifications.filtered(
                    lambda message, record=record: message.res_id == record.id
                ).partner_ids
                for record in many_records
            ],
            [users[index].partner_id for index in range(20)],
            "each notification reaches that record's own assignee and nobody else",
        )


@tagged("mail_followers", "post_install", "-at_install")
class RecipientsNotificationTest(MailCommon):
    """Test advanced and complex recipients computation / notification, such
    as multiple users, batch computation, ... Post install because we need the
    registry to be ready to send notifications."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # portal user for testing share status / internal subtypes
        cls.user_portal = cls._create_portal_user()
        cls.partner_portal = cls.user_portal.partner_id

        # simple customer
        cls.customer = cls.env["res.partner"].create(
            {
                "email": "customer@test.customer.com",
                "name": "Customer",
                "phone_ids": [
                    Command.create({"number": "+32455778899", "type": "landline"})
                ],
            }
        )

        # Simulate case of 2 users that got their partner merged
        cls.common_partner = cls.env["res.partner"].create(
            {
                "email": "common.partner@test.customer.com",
                "name": "Common Partner",
                "phone_ids": [
                    Command.create({"number": "+32455998877", "type": "landline"})
                ],
            }
        )
        cls.user_1, cls.user_2 = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                [
                    {
                        "group_ids": [(4, cls.env.ref("base.group_portal").id)],
                        "login": "_login_portal",
                        "notification_type": "email",
                        "partner_id": cls.common_partner.id,
                    },
                    {
                        "group_ids": [(4, cls.env.ref("base.group_user").id)],
                        "login": "_login_internal",
                        "notification_type": "inbox",
                        "partner_id": cls.common_partner.id,
                    },
                ]
            )
        )
        cls.env.flush_all()

    def assertRecipientsData(
        self, recipients_data, records, partners, partner_to_users=None
    ):
        """Custom assert as recipients structure is custom and may change due
        to some implementation choice."""
        if records:
            self.assertEqual(set(recipients_data.keys()), set(records.ids))
            record_ids = records.ids
        else:
            records, record_ids = [False], [0]
        for record, record_id in zip(records, record_ids, strict=True):
            record_data = recipients_data[record_id]
            self.assertEqual(set(record_data.keys()), set(partners.ids))
            for partner in partners:
                partner_data = record_data[partner.id]
                if partner_to_users and partner_to_users.get(
                    partner.id
                ):  # helps making test explicit
                    user = partner_to_users[partner.id]
                else:
                    user = next(
                        (user for user in partner.user_ids if not user.share),
                        self.env["res.users"],
                    )
                    if not user:
                        user = next(
                            (user for user in partner.user_ids), self.env["res.users"]
                        )
                self.assertEqual(partner_data["active"], partner.active)
                self.assertEqual(
                    partner_data["email_normalized"], partner.email_normalized
                )
                self.assertEqual(partner_data["lang"], partner.lang)
                self.assertEqual(partner_data["name"], partner.name)
                if user:
                    self.assertEqual(
                        partner_data["groups"], set(user.all_group_ids.ids)
                    )
                    self.assertEqual(partner_data["notif"], user.notification_type)
                    self.assertEqual(partner_data["uid"], user.id)
                else:
                    self.assertEqual(partner_data["groups"], set())
                    self.assertEqual(partner_data["notif"], "email")
                    self.assertFalse(partner_data["uid"])
                if record:
                    self.assertEqual(
                        partner_data["is_follower"],
                        partner in record.message_partner_ids,
                    )
                else:
                    self.assertFalse(partner_data["is_follower"])
                self.assertEqual(partner_data["share"], partner.partner_share)
                self.assertEqual(partner_data["ushare"], user.share)

    @users("employee")
    def test_notification_nodupe(self):
        """Check that we only create one mail.notification per partner."""
        # Trigger auto subscribe notification
        test = self.env["mail.test.track"].create(
            {"name": "Test Track", "user_id": self.user_2.id}
        )
        mail_message = self.env["mail.message"].search(
            [
                ("res_id", "=", test.id),
                ("model", "=", "mail.test.track"),
                ("message_type", "=", "user_notification"),
            ]
        )
        notif = self.env["mail.notification"].search(
            [
                ("mail_message_id", "=", mail_message.id),
                ("res_partner_id", "=", self.common_partner.id),
            ]
        )
        self.assertEqual(len(notif), 1)
        self.assertEqual(
            notif.notification_type,
            "inbox",
            "Multi users should take internal users if possible",
        )

        recipients_data = self.env["mail.followers"]._get_recipient_data(
            test,
            "comment",
            self.env.ref("mail.mt_comment").id,
            pids=self.common_partner.ids,
        )
        self.assertRecipientsData(
            recipients_data,
            test,
            self.common_partner + self.partner_employee,
            partner_to_users={self.common_partner.id: self.user_2},
        )

    @users("employee")
    @mute_logger("odoo.models.unlink")
    def test_notification_unlink(self):
        """Check that we unlink the created user_notification after unlinked the
        related document."""
        test = self.env["mail.test.track"].create(
            {"name": "Test Track", "user_id": self.user_1.id}
        )
        mail_message = self.env["mail.message"].search(
            [
                ("res_id", "=", test.id),
                ("model", "=", "mail.test.track"),
                ("message_type", "=", "user_notification"),
            ]
        )
        self.assertEqual(len(mail_message), 1)
        test.unlink()
        self.assertEqual(
            self.env["mail.message"].search_count(
                [
                    ("res_id", "=", test.id),
                    ("model", "=", "mail.test.track"),
                    ("message_type", "=", "user_notification"),
                ]
            ),
            0,
        )

    @users("employee")
    def test_notification_user_choice(self):
        """Check fetching user information when notifying someone with multiple
        users (more complex use case)."""
        company_other = (
            self.env["res.company"]
            .sudo()
            .create(
                {
                    "currency_id": self.env.ref("base.CAD").id,
                    "email": "company_other@test.example.com",
                    "name": "Company Other",
                }
            )
        )
        shared_partner = (
            self.env["res.partner"]
            .sudo()
            .create(
                {
                    "email": "common.partner@test.customer.com",
                    "name": "Common Partner",
                    "phone_ids": [
                        Command.create({"number": "+32455998877", "type": "landline"})
                    ],
                }
            )
        )
        cids = (company_other + self.company_admin).ids
        user_2_1, user_2_2, user_2_3 = (
            self.env["res.users"]
            .sudo()
            .with_context(no_reset_password=True)
            .create(
                [
                    {
                        "company_ids": [(6, 0, cids)],
                        "company_id": self.company_admin.id,
                        "group_ids": [(4, self.env.ref("base.group_portal").id)],
                        "login": "_login2_portal",
                        "notification_type": "email",
                        "partner_id": shared_partner.id,
                    },
                    {
                        "company_ids": [(6, 0, cids)],
                        "company_id": self.company_admin.id,
                        "group_ids": [(4, self.env.ref("base.group_user").id)],
                        "login": "_login2_internal",
                        "notification_type": "inbox",
                        "partner_id": shared_partner.id,
                    },
                    {
                        "company_ids": [(6, 0, cids)],
                        "company_id": company_other.id,
                        "group_ids": [
                            (4, self.env.ref("base.group_user").id),
                            (4, self.env.ref("base.group_partner_manager").id),
                        ],
                        "login": "_login2_manager",
                        "notification_type": "inbox",
                        "partner_id": shared_partner.id,
                    },
                ]
            )
        )
        (user_2_1 + user_2_2 + user_2_3).flush_recordset()

        # just ensure current share status
        self.assertFalse(shared_partner.partner_share)
        self.assertTrue(user_2_1.share)
        self.assertFalse(user_2_2.share or user_2_3.share)

        test = self.env["mail.test.track"].create(
            {"name": "Test Track", "user_id": False}
        )
        self.assertEqual(test.message_partner_ids, self.partner_employee)

        with self.assertSinglePostNotifications(
            [
                {
                    "group": "customer",
                    "partner": shared_partner,
                    "status": "sent",
                    "type": "inbox",
                }
            ],
            message_info={"content": "User Choice Notification"},
        ):
            test.message_post(
                body=Markup("<p>User Choice Notification</p>"),
                message_type="comment",
                partner_ids=shared_partner.ids,
                subtype_xmlid="mail.mt_comment",
            )

        recipients_data = self.env["mail.followers"]._get_recipient_data(
            test, "comment", self.env.ref("mail.mt_comment").id, pids=shared_partner.ids
        )
        self.assertRecipientsData(
            recipients_data,
            test,
            self.partner_employee + shared_partner,
            partner_to_users={shared_partner.id: user_2_2},
        )

    @users("employee")
    def test_recipients_fetch(self):
        test_records = self.env["mail.test.simple"].create(
            [
                {
                    "email_from": "ignasse@example.com",
                    "name": "Test %s" % idx,
                }
                for idx in range(5)
            ]
        )
        # make followers listen to notes to use it and check portal will never be notified of it (internal)
        test_records.message_follower_ids.sudo().write(
            {"subtype_ids": [(4, self.env.ref("mail.mt_note").id)]}
        )
        for test_record in test_records:
            self.assertEqual(test_record.message_partner_ids, self.env.user.partner_id)

        test_records[0].message_subscribe(self.partner_portal.ids)
        self.assertNotIn(
            self.env.ref("mail.mt_note"),
            test_records[0]
            .message_follower_ids.filtered(
                lambda fol: fol.partner_id == self.partner_portal
            )
            .subtype_ids,
            "Portal user should not follow notes by default",
        )

        # just fetch followers
        recipients_data = self.env["mail.followers"]._get_recipient_data(
            test_records[0], "comment", self.env.ref("mail.mt_comment").id, pids=None
        )
        self.assertRecipientsData(
            recipients_data,
            test_records[0],
            self.env.user.partner_id + self.partner_portal,
        )

        # followers + additional recipients
        recipients_data = self.env["mail.followers"]._get_recipient_data(
            test_records[0],
            "comment",
            self.env.ref("mail.mt_comment").id,
            pids=(self.customer + self.common_partner + self.partner_admin).ids,
        )
        self.assertRecipientsData(
            recipients_data,
            test_records[0],
            self.env.user.partner_id
            + self.partner_portal
            + self.customer
            + self.common_partner
            + self.partner_admin,
        )

        # ensure filtering on internal: should exclude Portal even if misconfiguration
        follower_portal = (
            test_records[0]
            .message_follower_ids.filtered(
                lambda fol: fol.partner_id == self.partner_portal
            )
            .sudo()
        )
        follower_portal.write({"subtype_ids": [(4, self.env.ref("mail.mt_note").id)]})
        follower_portal.flush_recordset()
        recipients_data = self.env["mail.followers"]._get_recipient_data(
            test_records[0],
            "comment",
            self.env.ref("mail.mt_note").id,
            pids=(self.common_partner + self.partner_admin).ids,
        )
        self.assertRecipientsData(
            recipients_data,
            test_records[0],
            self.env.user.partner_id + self.common_partner + self.partner_admin,
        )

        # ensure filtering on subtype: should exclude Portal as it does not follow comment anymore
        follower_portal.write(
            {"subtype_ids": [(3, self.env.ref("mail.mt_comment").id)]}
        )
        recipients_data = self.env["mail.followers"]._get_recipient_data(
            test_records[0],
            "comment",
            self.env.ref("mail.mt_comment").id,
            pids=(self.common_partner + self.partner_admin).ids,
        )
        self.assertRecipientsData(
            recipients_data,
            test_records[0],
            self.env.user.partner_id + self.common_partner + self.partner_admin,
        )

        # check without subtype
        recipients_data = self.env["mail.followers"]._get_recipient_data(
            test_records[0],
            "comment",
            False,
            pids=(self.common_partner + self.partner_admin).ids,
        )
        self.assertRecipientsData(
            recipients_data, test_records[0], self.common_partner + self.partner_admin
        )

        # multi mode
        test_records[1].message_subscribe(self.partner_portal.ids)
        test_records[0:4].message_subscribe(self.common_partner.ids)
        recipients_data = self.env["mail.followers"]._get_recipient_data(
            test_records,
            "comment",
            self.env.ref("mail.mt_comment").id,
            pids=self.partner_admin.ids,
        )
        # 0: portal is follower but does not follow comment + common partner (+ admin as pid)
        recipients_data_1 = {
            r: recipients_data[r] for r in recipients_data if r in test_records[0:1].ids
        }
        self.assertRecipientsData(
            recipients_data_1,
            test_records[0:1],
            self.env.user.partner_id + self.common_partner + self.partner_admin,
        )
        # 1: portal is follower with comment + common partner (+ admin as pid)
        recipients_data_1 = {
            r: recipients_data[r] for r in recipients_data if r in test_records[1:2].ids
        }
        self.assertRecipientsData(
            recipients_data_1,
            test_records[1:2],
            self.env.user.partner_id
            + self.common_partner
            + self.partner_portal
            + self.partner_admin,
        )
        # 2-3: common partner (+ admin as pid)
        recipients_data_2 = {
            r: recipients_data[r] for r in recipients_data if r in test_records[2:4].ids
        }
        self.assertRecipientsData(
            recipients_data_2,
            test_records[2:4],
            self.env.user.partner_id + self.common_partner + self.partner_admin,
        )
        # 4+: env user partner (+ admin as pid)
        recipients_data_3 = {
            r: recipients_data[r] for r in recipients_data if r in test_records[4:].ids
        }
        self.assertRecipientsData(
            recipients_data_3,
            test_records[4:],
            self.env.user.partner_id + self.partner_admin,
        )

        # multi mode without subtype: an explicit pid is a recipient of *every*
        # record in scope, exactly as it is with a subtype above. 'common_partner'
        # follows records 0-3 but not 4, and is asked for as a pid: it must show
        # up on record 4 too, as a non-follower. The subtype-less query used to
        # answer this shape with its own SQL that emitted a row only for the
        # records a pid actually followed, so a partner following some of the
        # batch went missing from the rest of it.
        recipients_data = self.env["mail.followers"]._get_recipient_data(
            test_records,
            "comment",
            False,
            pids=(self.common_partner + self.partner_admin).ids,
        )
        self.assertRecipientsData(
            recipients_data, test_records, self.common_partner + self.partner_admin
        )
        for record in test_records:
            self.assertEqual(
                recipients_data[record.id][self.common_partner.id]["is_follower"],
                self.common_partner in record.message_partner_ids,
            )

        # 'user_notification' contacts the pids only, whatever the subtype says
        recipients_data = self.env["mail.followers"]._get_recipient_data(
            test_records,
            "user_notification",
            self.env.ref("mail.mt_comment").id,
            pids=self.partner_admin.ids,
        )
        self.assertRecipientsData(recipients_data, test_records, self.partner_admin)

        # multi mode, pids only
        recipients_data = self.env["mail.followers"]._get_recipient_data(
            test_records,
            "comment",
            False,
            pids=(self.env.user.partner_id + self.partner_admin).ids,
        )
        self.assertRecipientsData(
            recipients_data, test_records, self.env.user.partner_id + self.partner_admin
        )

        # on mixin.mail.thread, False everywhere: pathologic case
        test_partners = self.partner_admin + self.partner_employee + self.common_partner
        recipients_data = self.env["mail.followers"]._get_recipient_data(
            self.env["mixin.mail.thread"], False, False, pids=test_partners.ids
        )
        self.assertRecipientsData(recipients_data, False, test_partners)

    def test_subscribe_post_author(self):
        """Test author is added in followers, unless it is archived / odoobot"""
        # some automated action post on behalf of author
        test_record = self.env["mail.test.simple"].create({"name": "Test"})
        self.partner_root.active = (
            True  # edge case, people activating Odoobot partner (not user)
        )
        (
            self.user_1 + self.user_2
        ).active = False  # archived users should not be subscribed
        self.user_1.partner_id.active = (
            False  # archived authors should not be subscribed
        )
        self.assertFalse(test_record.message_partner_ids)
        for user, author, exp_followers in [
            # active user = real author
            (self.user_employee, self.user_2.partner_id, self.user_employee.partner_id),
            # inactive user -> check for author
            (self.user_2, self.user_employee.partner_id, self.user_employee.partner_id),
            (
                self.user_2,
                self.user_1.partner_id,
                self.env["res.partner"],
            ),  # no inactive !
            (
                self.user_2,
                self.user_root.partner_id,
                self.env["res.partner"],
            ),  # no odoobot !
        ]:
            with self.subTest(user=user.name, author=author.name):
                test_record.with_user(user).message_post(
                    author_id=author.id,
                    body="Youpie",
                    message_type="comment",
                    subtype_id=self.env.ref("mail.mt_comment").id,
                )
                self.assertEqual(test_record.message_partner_ids, exp_followers)
                if exp_followers:
                    test_record.message_unsubscribe(partner_ids=exp_followers.ids)


@tagged("mail_followers", "post_install", "-at_install")
class UnfollowLinkTest(MailCommon, HttpCase):
    """Test unfollow links, notably used in notification emails"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_portal = cls._create_portal_user()
        cls.partner_portal = cls.user_portal.partner_id
        cls.test_record = (
            cls.env["mail.test.simple"]
            .with_context(cls._test_context)
            .create({"name": "Test"})
        )
        cls.test_record_copy = cls.test_record.copy()
        cls.test_record_unfollow = (
            cls.env["mail.test.simple.unfollow"]
            .with_context(cls._test_context)
            .create({"name": "unfollow"})
        )
        cls.partner_without_user = cls.env["res.partner"].create(
            {
                "name": "Dave",
                "email": "dave@odoo.com",
            }
        )
        cls.user_employee.write({"notification_type": "email"})

    def _message_unsubscribe_unreadable_record(self, user):
        def raise_access_error(*args, **kwargs):
            raise AccessError("Unreadable")

        with patch.object(
            self.test_record.__class__, "check_access", side_effect=raise_access_error
        ):
            self.test_record.with_user(user).message_unsubscribe(user.partner_id.ids)

    def _test_tampered_unfollow_url(self, record, unfollow_url, partner):
        """Test that tampered urls doesn't work.

        Test that:
        - when the following parameters are altered, the browsing the URL returns
        a 403 and doesn't unsubscribe the partner.
        - when trying to use the same URL with another partner, it also returns a
        403 and doesn't unsubscribe the other partner.
        """
        for param, value in (
            ("token", "0000000000000000000000000000000000000000"),
            ("model", "mail.test.gateway"),
            ("res_id", self.test_record_copy.id),
            ("pid", self.partner_admin.id),
        ):
            with self.subTest(f"Tampered {param}"):
                tampered_unfollow_url = self._url_update_query_parameters(
                    unfollow_url, **{param: value}
                )
                response = self.url_open(tampered_unfollow_url)
                self.assertEqual(response.status_code, 403)
                self.assertIn(partner, record.message_partner_ids)

    def _test_unfollow_url(self, record, unfollow_url, partner):
        """Test that the unfollow url works.

        Test that: that browsing the unfollow URL unsubscribe the user from the record
        """
        with self.subTest("Legitimate unfollow"):
            # We test that the URL still work a second time if the user has been re-added
            for _ in range(2):
                try:
                    self.assertIn(partner, record.message_partner_ids)
                    response = self.url_open(unfollow_url)
                    self.assertEqual(response.status_code, 200)
                    self.assertNotIn(partner, record.message_partner_ids)
                    self.assertEqual(urlparse(response.url).path, "/mail/unfollow")
                    self.assertIn(
                        "You are no longer following the document", response.text
                    )
                    self.assertIn("o_access_record_link", response.text)
                finally:
                    record._message_subscribe(partner_ids=partner.ids)

    def test_assert_initial_data(self):
        """Test some initial value."""
        record_employee = self.test_record.with_user(self.user_employee)
        record_employee.check_access("read")
        record_portal = self.test_record.with_user(self.user_portal)
        with self.assertRaises(AccessError):
            record_portal.check_access("write")
        for template_ref in (
            "mail.mail_notification_layout",
            "mail.mail_notification_light",
        ):
            with self.subTest(f"Unfollow link in {template_ref}"):
                mail_template_arch = self.env.ref(template_ref).arch
                self.assertIn("/mail/unfollow", mail_template_arch)
                # asked through the method the send path uses, rather than
                # through a module-level regex a test reached in for: the
                # question is whether the layout keeps the link *inside* the
                # block, and only the stripper knows where the block ends
                self.assertNotIn(
                    "/mail/unfollow",
                    self.env["mail.mail"]._strip_unfollow_block(mail_template_arch),
                )

    @users("employee")
    @mute_logger("odoo.models")
    def test_inbox_unfollow_information(self):
        """Check follow-up information for displaying inbox messages used to
        implement "unfollow" in the inbox.

        Note that the actual mechanism to unfollow a record from a message is
        tested in the client part.
        """
        self.user_employee.write({"notification_type": "inbox"})

        test_record = self.env["mail.test.simple"].browse(self.test_record.ids)
        _message = test_record.with_user(self.user_admin).message_post(
            body="test message",
            subtype_id=self.env.ref("mail.mt_comment").id,
            partner_ids=self.partner_employee.ids,
        )
        # The user doesn't follow the record
        self.authenticate(self.env.user.login, self.env.user.login)
        message_data = self.call_jsonrpc("/mail/inbox/messages")["data"]
        self.assertFalse(message_data["mixin.mail.thread"][0]["selfFollower"])
        self.assertFalse(
            message_data.get("mail.followers"), "Should not have void followers data"
        )
        self.assertFalse(test_record.with_user(self.user_employee).message_is_follower)

        # The user follows the record
        test_record._message_subscribe(partner_ids=self.env.user.partner_id.ids)
        follower = test_record.message_follower_ids.filtered(
            lambda follower: follower.partner_id == self.env.user.partner_id
        )
        message_data = self.call_jsonrpc("/mail/inbox/messages")["data"]
        self.assertEqual(
            message_data["mail.followers"],
            [
                {
                    "id": follower.id,
                    "is_active": True,
                    "partner_id": self.env.user.partner_id.id,
                },
            ],
        )
        self.assertEqual(
            message_data["mixin.mail.thread"][0]["selfFollower"],
            follower.id,
            "Should have follower ID",
        )

    @mute_logger(
        "odoo.addons.base.models",
        "odoo.addons.mail.controllers.mail",
        "odoo.http",
        "odoo.models",
    )
    def test_notification_email_unfollow_link(self):
        """Internal user must receive an unfollow URL, that cannot be tampered
        and redirects to the correct page.
        """
        for test_partners, test_record, exp_has_url in [
            (self.partner_employee, self.test_record, [True]),
            # customer should not receive an unfollow URL
            (self.partner_without_user, self.test_record, [False]),
            (self.partner_portal, self.test_record, [False]),
            # always unfollow link (model definition)
            (self.partner_without_user, self.test_record_unfollow, [True]),
            (self.partner_portal, self.test_record_unfollow, [True]),
            # multi partners
            (
                self.partner_without_user + self.partner_portal + self.partner_employee,
                self.test_record,
                [False, False, True],
            ),
            (
                self.partner_without_user + self.partner_portal + self.partner_employee,
                self.test_record_unfollow,
                [True, True, True],
            ),
        ]:
            with self.subTest(partners=test_partners.mapped("name")):
                # Test that the user receives an unfollow URL when following the record
                test_record._message_subscribe(partner_ids=test_partners.ids)
                unfollow_urls = self._message_post_and_get_unfollow_urls(
                    test_record, test_partners
                )
                for test_partner, unfollow_url, has_url in zip(
                    test_partners, unfollow_urls, exp_has_url, strict=True
                ):
                    self.assertEqual(bool(unfollow_url), has_url)

                    # Test unfollowing URL when user is not logged
                    if has_url:
                        self.authenticate(None, None)
                        self._test_unfollow_url(test_record, unfollow_url, test_partner)
                        self._test_tampered_unfollow_url(
                            test_record, unfollow_url, test_partner
                        )

                        if test_partner == self.partner_employee:
                            # Test unfollowing URL when user is logged
                            self.authenticate(
                                self.user_employee.login, self.user_employee.login
                            )
                            self._test_unfollow_url(
                                test_record, unfollow_url, test_partner
                            )

                # Test that the user doesn't receive the unfollow URL when not following the record
                test_record.message_unsubscribe(partner_ids=test_partners.ids)
                unfollow_urls = self._message_post_and_get_unfollow_urls(
                    test_record, test_partners
                )
                for _test_partner, unfollow_url in zip(
                    test_partners, unfollow_urls, strict=True
                ):
                    self.assertFalse(unfollow_url)

    def test_unsubscribe_unreadable(self):
        """Check internal can always unsubscribe form records while portal are
        limited to records they can access. Other records are considered as customer
        oriented and we don't want to lose emails."""
        for user, can_unsubscribe in [
            (self.user_employee, True),
            (self.user_portal, False),
        ]:
            self.test_record._message_subscribe(partner_ids=user.partner_id.ids)
            self.assertIn(user.partner_id, self.test_record.message_partner_ids)
            if can_unsubscribe:
                self._message_unsubscribe_unreadable_record(user)
                self.assertNotIn(user.partner_id, self.test_record.message_partner_ids)
            else:
                with self.assertRaises(AccessError):
                    self._message_unsubscribe_unreadable_record(user)
