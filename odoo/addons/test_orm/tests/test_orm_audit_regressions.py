from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.service.model import call_kw
from odoo.tests.common import TransactionCase


class TestCheckAccessOverRpc(TransactionCase):
    """check_access binds to the records it is asked about: over call_kw the
    ids travel like has_access's, not as a model-level call that drops them."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create(
            {
                "name": "rpc_check_access",
                "login": "rpc_check_access",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

    def test_check_access_over_rpc_refuses_a_record_the_rules_forbid(self):
        users = self.env["res.users"].with_user(self.user)
        admin = self.env.ref("base.user_admin")
        self.assertFalse(call_kw(users, "has_access", [[admin.id], "write"], {}))
        with self.assertRaises(AccessError):
            call_kw(users, "check_access", [[admin.id], "write"], {})

    def test_check_access_over_rpc_passes_a_record_the_rules_allow(self):
        users = self.env["res.users"].with_user(self.user)
        self.assertIsNone(call_kw(users, "check_access", [[self.user.id], "read"], {}))


class TestCompanyDependentRestrictGuard(TransactionCase):
    """A company-dependent many2one with ondelete=restrict refuses the delete
    of the record it references, and names that record -- not whichever
    company's value comes first in the stored object."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_company = cls.env["res.company"].create({"name": "Other Co"})
        cls.first_tag, cls.second_tag = cls.env["test_orm.multi.tag"].create(
            [{"name": "first"}, {"name": "second"}]
        )
        holder = cls.env["test_orm.company"].create({"kept_tag_id": cls.first_tag.id})
        holder.with_company(cls.other_company).kept_tag_id = cls.second_tag
        cls.holder = holder
        cls.env.flush_all()

    def test_deleting_the_second_company_value_names_that_record(self):
        with self.assertRaises(UserError) as caught:
            self.second_tag.unlink()
        message = str(caught.exception)
        self.assertIn(f"test_orm.multi.tag({self.second_tag.id},)", message)
        self.assertNotIn(f"test_orm.multi.tag({self.first_tag.id},)", message)

    def test_deleting_the_first_company_value_names_that_record(self):
        with self.assertRaises(UserError) as caught:
            self.first_tag.unlink()
        message = str(caught.exception)
        self.assertIn(f"test_orm.multi.tag({self.first_tag.id},)", message)
        self.assertNotIn(f"test_orm.multi.tag({self.second_tag.id},)", message)

    def test_an_unreferenced_record_still_deletes(self):
        free = self.env["test_orm.multi.tag"].create({"name": "free"})
        free.unlink()
        self.assertFalse(free.exists())


class TestOne2oneAgainstTheRealIndex(TransactionCase):
    """A One2one is held by a unique index in the database, and the DB-free
    tier does not enforce `index="unique"` -- so the release must be pinned
    where the index exists."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Seat = cls.env["test_orm.seat"]
        cls.Holder = cls.env["test_orm.seat.holder"]

    def test_the_inverse_column_really_carries_a_unique_index(self):
        self.env.cr.execute(
            """SELECT indexdef FROM pg_indexes
               WHERE tablename = 'test_orm_seat' AND indexdef ILIKE '%%holder_id%%'"""
        )
        defs = [row[0] for row in self.env.cr.fetchall()]
        self.assertTrue(
            any("UNIQUE" in d.upper() for d in defs),
            f"test premise: no unique index on holder_id, got {defs}",
        )

    def test_linking_another_seat_releases_the_held_one(self):
        first, second = self.Seat.create([{"name": "1"}, {"name": "2"}])
        holder = self.Holder.create({"name": "h", "seat_id": [Command.link(first.id)]})
        self.env.flush_all()

        holder.write({"seat_id": [Command.link(second.id)]})
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(holder.seat_id, second)
        self.assertFalse(first.holder_id)
        self.assertEqual(self.Seat.search_count([("holder_id", "=", holder.id)]), 1)

    def test_creating_another_seat_releases_the_held_one(self):
        first = self.Seat.create({"name": "1"})
        holder = self.Holder.create({"name": "h", "seat_id": [Command.link(first.id)]})
        self.env.flush_all()

        holder.write({"seat_id": [Command.create({"name": "2"})]})
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(holder.seat_id.name, "2")
        self.assertFalse(first.holder_id)
        self.assertEqual(self.Seat.search_count([("holder_id", "=", holder.id)]), 1)

    def test_two_holders_cannot_share_a_seat(self):
        seat = self.Seat.create({"name": "1"})
        first = self.Holder.create({"name": "a", "seat_id": [Command.link(seat.id)]})
        self.env.flush_all()
        second = self.Holder.create({"name": "b"})
        with self.assertRaises(UserError):
            second.write({"seat_id": [Command.link(seat.id)]})
        self.assertEqual(seat.holder_id, first)
