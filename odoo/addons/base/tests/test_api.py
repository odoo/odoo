from odoo import Command, models
from odoo.exceptions import AccessError
from odoo.models import PREFETCH_MAX
from odoo.tools import lazy, mute_logger, unique

from odoo.addons.base.tests.common import SavepointCaseWithUserDemo


class TestAPI(SavepointCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._load_partners_set()

    def assertIsRecordset(self, value, model):
        self.assertIsInstance(value, models.BaseModel)
        self.assertEqual(value._name, model)

    def assertIsRecord(self, value, model):
        self.assertIsRecordset(value, model)
        self.assertTrue(len(value) <= 1)

    def assertIsNull(self, value, model):
        self.assertIsRecordset(value, model)
        self.assertFalse(value)

    @mute_logger("odoo.models")
    def test_00_query(self):
        domain = [("name", "ilike", "j"), ("id", "in", self.partners.ids)]
        partners = self.env["res.partner"].search(domain)

        self.assertTrue(partners)

        self.assertIsRecordset(partners, "res.partner")
        for p in partners:
            self.assertIsRecord(p, "res.partner")

    @mute_logger("odoo.models")
    def test_01_query_offset(self):
        partners1 = self.env["res.partner"].search(
            [("id", "in", self.partners.ids)], offset=5
        )
        partners2 = self.env["res.partner"].search([("id", "in", self.partners.ids)])[
            5:
        ]
        self.assertIsRecordset(partners1, "res.partner")
        self.assertIsRecordset(partners2, "res.partner")
        self.assertEqual(list(partners1), list(partners2))

    @mute_logger("odoo.models")
    def test_02_query_limit(self):
        partners1 = self.env["res.partner"].search(
            [("id", "in", self.partners.ids)], order="id asc", limit=5
        )
        partners2 = self.env["res.partner"].search(
            [("id", "in", self.partners.ids)], order="id asc"
        )[:5]
        self.assertIsRecordset(partners1, "res.partner")
        self.assertIsRecordset(partners2, "res.partner")
        self.assertEqual(list(partners1), list(partners2))

    @mute_logger("odoo.models")
    def test_03_query_offset_limit(self):
        partners1 = self.env["res.partner"].search(
            [("id", "in", self.partners.ids)], order="id asc", offset=3, limit=7
        )
        partners2 = self.env["res.partner"].search(
            [("id", "in", self.partners.ids)], order="id asc"
        )[3:10]
        self.assertIsRecordset(partners1, "res.partner")
        self.assertIsRecordset(partners2, "res.partner")
        self.assertEqual(list(partners1), list(partners2))

    @mute_logger("odoo.models")
    def test_04_query_count(self):
        self.cr.execute("SELECT COUNT(*) FROM res_partner WHERE active")
        count1 = self.cr.fetchone()[0]
        count2 = self.env["res.partner"].search_count([])
        self.assertIsInstance(count1, int)
        self.assertIsInstance(count2, int)
        self.assertEqual(count1, count2)

    @mute_logger("odoo.models")
    def test_05_immutable(self):
        domain = [("name", "ilike", "g"), ("id", "in", self.partners.ids)]
        partners = self.env["res.partner"].search(domain)
        self.assertTrue(partners)
        ids = partners.ids

        partners.write({"active": False})
        self.assertEqual(ids, partners.ids)

        partners2 = self.env["res.partner"].search(domain)
        self.assertFalse(partners2)

    @mute_logger("odoo.models")
    def test_06_fields(self):
        user = self.env.user
        self.assertIsRecord(user, "res.users")
        self.assertIsRecord(user.partner_id, "res.partner")
        self.assertIsRecordset(user.group_ids, "res.groups")

        for name, field in self.partners._fields.items():
            if field.type == "many2one":
                for p in self.partners:
                    self.assertIsRecord(p[name], field.comodel_name)
            elif field.type == "reference":
                for p in self.partners:
                    if p[name]:
                        self.assertIsRecord(p[name], field.comodel_name)
            elif field.type in ("one2many", "many2many"):
                for p in self.partners:
                    self.assertIsRecordset(p[name], field.comodel_name)

    @mute_logger("odoo.models")
    def test_07_null(self):
        partner = self.env["res.partner"].search(
            [("parent_id", "=", False), ("id", "in", self.partners.ids)]
        )[0]

        self.assertTrue(partner)
        self.assertIsRecord(partner, "res.partner")

        self.assertFalse(partner.parent_id)
        self.assertIsNull(partner.parent_id, "res.partner")

        self.assertIs(partner.parent_id.id, False)

        self.assertFalse(partner.parent_id.user_id)
        self.assertIsNull(partner.parent_id.user_id, "res.users")

        self.assertIs(partner.parent_id.user_id.name, False)

        self.assertFalse(partner.parent_id.user_id.group_ids)
        self.assertIsRecordset(partner.parent_id.user_id.group_ids, "res.groups")

    @mute_logger("odoo.models")
    def test_40_new_new(self):
        partners = self.env["res.partner"].search(
            [("name", "ilike", "g"), ("id", "in", self.partners.ids)]
        )
        self.assertTrue(partners)

        partners.write({"active": False})
        for p in partners:
            self.assertFalse(p.active)

    @mute_logger("odoo.models")
    def test_45_new_new(self):
        partners = self.env["res.partner"].search(
            [("name", "ilike", "g"), ("id", "in", self.partners.ids)]
        )
        self.assertTrue(partners)

        for p in partners:
            p.write({"active": False})
        for p in partners:
            self.assertFalse(p.active)

    @mute_logger("odoo.models")
    @mute_logger("odoo.addons.base.models.ir_model")
    def test_50_environment(self):
        partners = self.env["res.partner"].search(
            [("name", "ilike", "j"), ("id", "in", self.partners.ids)]
        )
        self.assertEqual(partners.env, self.env)
        for x in (partners, partners[0], partners[0].company_id):
            self.assertEqual(x.env, self.env)
        for p in partners:
            self.assertEqual(p.env, self.env)

        _ = partners[0].company_id.name
        partners[0].company_id.write({"name": "Fools"})

        demo = self.env["res.users"].create(
            {
                "name": "test_environment_demo",
                "login": "test_environment_demo",
                "password": "test_environment_demo",
            }
        )
        demo_env = self.env(user=demo)
        self.assertNotEqual(demo_env, self.env)

        self.assertEqual(partners.env, self.env)
        for x in (partners, partners[0], partners[0].company_id):
            self.assertEqual(x.env, self.env)
        for p in partners:
            self.assertEqual(p.env, self.env)

        demo_partners = partners.with_user(demo)
        self.assertEqual(demo_partners.env, demo_env)
        for x in (demo_partners, demo_partners[0], demo_partners[0].company_id):
            self.assertEqual(x.env, demo_env)
        for p in demo_partners:
            self.assertEqual(p.env, demo_env)

        demo_partner = (
            self.env["res.partner"]
            .search([("name", "=", "Landon Roberts")])
            .with_user(demo)
        )
        self.assertTrue(
            demo_partner.company_id,
            "This partner is supposed to be linked to a company",
        )
        _ = demo_partner.company_id.name
        with self.assertRaises(AccessError):
            demo_partner.company_id.write({"name": "Pricks"})

        demo.write({"group_ids": [Command.clear()]})

        with self.assertRaises(AccessError):
            _ = demo_partner.company_id.name

    @mute_logger("odoo.models")
    def test_60_cache(self):
        Partners = self.env["res.partner"]
        data = {
            "partner One": ["Partner One - One", "Partner One - Two"],
            "Partner Two": ["Partner Two - One"],
            "Partner Three": ["Partner Three - One"],
        }
        pids = [
            Partners.create(
                {
                    "name": p,
                    "child_ids": [Command.create({"name": c}) for c in data[p]],
                }
            ).id
            for p in data
        ]

        partners = Partners.search([("id", "in", pids)])
        partner1, partner2 = partners[0], partners[1]
        children1, children2 = partner1.child_ids, partner2.child_ids
        self.assertTrue(children1)
        self.assertTrue(children2)

        child = children1[0]
        self.assertEqual(child.parent_id, partner1)
        self.assertIn(child, partner1.child_ids)
        self.assertNotIn(child, partner2.child_ids)

        for p in partners:
            _ = p.name, p.company_id.name, p.user_id.name, p.contact_address
        self.env.cache.check(self.env)

        child.write({"parent_id": partner2.id})
        self.env.cache.check(self.env)

        self.assertEqual(child.parent_id, partner2)
        self.assertNotIn(child, partner1.child_ids)
        self.assertIn(child, partner2.child_ids)
        self.assertEqual(set(partner1.child_ids + child), set(children1))
        self.assertEqual(set(partner2.child_ids), set(children2 + child))
        self.env.cache.check(self.env)

        child.unlink()
        self.env.cache.check(self.env)

        self.assertEqual(set(partner1.child_ids), set(children1) - {child})
        self.assertEqual(set(partner2.child_ids), set(children2))
        self.env.cache.check(self.env)

        partner = partner1
        _ = partner.country_id, partner.child_ids
        data = partner._convert_to_write(partner._cache)
        self.assertEqual(data["country_id"], partner.country_id.id)
        self.assertEqual(data["child_ids"], [Command.set(partner.child_ids.ids)])

    @mute_logger("odoo.models")
    def test_60_prefetch(self):
        partners = self.env["res.partner"].search(
            [("id", "in", self.partners.ids)], limit=PREFETCH_MAX
        )
        self.assertTrue(len(partners) > 1)

        self.assertItemsEqual(partners.ids, partners._prefetch_ids)

        for partner in partners:
            state = partner.state_id
            break
        partner_ids_with_field = [
            partner.id for partner in partners if "state_id" in partner._cache
        ]
        self.assertItemsEqual(partner_ids_with_field, partners.ids)

        state_ids = {
            partner._cache["state_id"]
            for partner in partners
            if partner._cache["state_id"] is not None
        }
        self.assertTrue(len(state_ids) > 1)
        self.assertItemsEqual(state_ids, state._prefetch_ids)

        for partner in partners:
            if partner.state_id:
                _ = partner.state_id.name
                break
        state_ids_with_field = [
            st.id for st in partners.state_id if "name" in st._cache
        ]
        self.assertItemsEqual(state_ids_with_field, state_ids)

    @mute_logger("odoo.models")
    def test_60_prefetch_model(self):
        partners = self.env["res.partner"].search(
            [("id", "in", self.partners.ids)], limit=PREFETCH_MAX
        )
        self.assertTrue(partners)

        def same_prefetch(a, b):
            self.assertEqual(set(a._prefetch_ids), set(b._prefetch_ids))

        def diff_prefetch(a, b):
            self.assertNotEqual(set(a._prefetch_ids), set(b._prefetch_ids))

        diff_prefetch(partners, partners.browse())
        diff_prefetch(partners, partners[:5])

        same_prefetch(partners, partners[0])
        same_prefetch(partners, partners.browse(partners.ids))
        same_prefetch(partners, partners.with_user(self.user_demo))
        same_prefetch(partners, partners.with_context(active_test=False))
        same_prefetch(partners, partners[:10].with_prefetch(partners._prefetch_ids))

        self.assertEqual(type(partners).country_id.type, "many2one")
        self.assertEqual(type(partners).bank_account_ids.type, "one2many")
        self.assertEqual(type(partners).tag_ids.type, "many2many")

        vals0 = {
            "name": "Empty relational fields",
            "country_id": False,
            "bank_account_ids": [],
            "tag_ids": [],
        }
        vals1 = {
            "name": "Non-empty relational fields",
            "country_id": self.ref("base.be"),
            "bank_account_ids": [Command.create({"acc_number": "FOO42"})],
            "tag_ids": [Command.link(self.partner_category.id)],
        }
        partners = partners.create(vals0) + partners.create(vals1)
        for partner in partners:
            same_prefetch(partner, partners)
            same_prefetch(partner.country_id, partners.country_id)
            same_prefetch(partner.bank_account_ids, partners.bank_account_ids)
            same_prefetch(partner.tag_ids, partners.tag_ids)

    @mute_logger("odoo.models")
    def test_60_prefetch_read(self):
        Partner = self.env["res.partner"]
        field = type(Partner).type_address_label
        self.assertTrue(field.compute and not field.store)

        partner1 = Partner.create({"name": "Foo"})
        partner2 = Partner.create({"name": "Bar", "parent_id": partner1.id})
        self.assertEqual(partner1.child_ids, partner2)

        self.env.clear()
        partner1 = partner1.with_prefetch()
        partner1.read(["type_address_label"])
        self.assertIn("type_address_label", partner1._cache)
        self.assertNotIn("type_address_label", partner2._cache)

        self.env.clear()
        partner1 = partner1.with_prefetch()
        partner1.read(["child_ids", "type_address_label"])
        self.assertIn("type_address_label", partner1._cache)
        self.assertNotIn("type_address_label", partner2._cache)

    def test_60_reversed(self):
        records = self.partners
        self.assertGreater(len(records), 1)

        self.assertEqual(list(reversed(records)), list(reversed(list(records))))

        first = next(iter(records))
        last = next(reversed(records))
        self.assertEqual(first, records[0])
        self.assertEqual(last, records[-1])

        prefetch_ids = records.ids
        reversed_ids = [record.id for record in reversed(records)]

        self.assertEqual(list(first._prefetch_ids), prefetch_ids)
        self.assertEqual(list(last._prefetch_ids), reversed_ids)

        self.assertEqual(list(reversed(first._prefetch_ids)), reversed_ids)
        self.assertEqual(list(reversed(last._prefetch_ids)), prefetch_ids)

        prefetch_ids = records.state_id.ids
        reversed_ids = list(
            unique(
                record.state_id.id for record in reversed(records) if record.state_id
            )
        )

        self.assertEqual(list(first.state_id._prefetch_ids), prefetch_ids)
        self.assertEqual(list(last.state_id._prefetch_ids), reversed_ids)

        self.assertEqual(list(reversed(first.state_id._prefetch_ids)), reversed_ids)
        self.assertEqual(list(reversed(last.state_id._prefetch_ids)), prefetch_ids)

        prefetch_ids = records.child_ids.ids
        reversed_ids = list(
            unique(
                child.id for record in reversed(records) for child in record.child_ids
            )
        )

        self.assertEqual(list(first.child_ids._prefetch_ids), prefetch_ids)
        self.assertEqual(list(last.child_ids._prefetch_ids), reversed_ids)

        self.assertEqual(list(reversed(first.child_ids._prefetch_ids)), reversed_ids)
        self.assertEqual(list(reversed(last.child_ids._prefetch_ids)), prefetch_ids)

    @mute_logger("odoo.models")
    def test_70_one(self):
        ps = self.env["res.partner"].search(
            [("name", "ilike", "a"), ("id", "in", self.partners.ids)]
        )
        self.assertTrue(len(ps) > 1)
        with self.assertRaises(ValueError):
            ps.check_singleton()

        p1 = ps[0]
        self.assertEqual(len(p1), 1)
        self.assertEqual(p1.check_singleton(), p1)

        p0 = self.env["res.partner"].browse()
        self.assertEqual(len(p0), 0)
        with self.assertRaises(ValueError):
            p0.check_singleton()

    @mute_logger("odoo.models")
    def test_80_contains(self):
        p1 = self.partners[0]
        ps = self.partners
        self.assertTrue(p1 in ps)

        with self.assertRaisesRegex(
            TypeError, r"unsupported operand types in: 42 in res\.partner.*"
        ):
            _ = 42 in ps
        with self.assertRaisesRegex(
            TypeError,
            r"inconsistent models in: ir\.ui\.menu.* in res\.partner.*",
        ):
            _ = self.env["ir.ui.menu"] in ps

    @mute_logger("odoo.models")
    def test_80_lazy_contains(self):
        p1 = lazy(lambda: self.partners[0])
        ps = lazy(lambda: self.partners)
        self.assertTrue(p1 in ps)

        with self.assertRaisesRegex(
            TypeError, r"unsupported operand types in: 42 in res\.partner.*"
        ):
            _ = lazy(lambda: 42) in ps
        with self.assertRaisesRegex(
            TypeError,
            r"inconsistent models in: ir\.ui\.menu.* in res\.partner.*",
        ):
            _ = lazy(lambda: self.env["ir.ui.menu"]) in ps

    @mute_logger("odoo.models")
    def test_80_set_operations(self):
        pa = self.env["res.partner"].search(
            [("name", "ilike", "a"), ("id", "in", self.partners.ids)]
        )
        pb = self.env["res.partner"].search(
            [("name", "ilike", "b"), ("id", "in", self.partners.ids)]
        )

        self.assertTrue(pa)
        self.assertTrue(pb)
        self.assertTrue(set(pa) & set(pb))

        concat = pa + pb
        self.assertEqual(list(concat), list(pa) + list(pb))
        self.assertEqual(len(concat), len(pa) + len(pb))

        difference = pa - pb
        self.assertEqual(len(difference), len(set(difference)))
        self.assertEqual(set(difference), set(pa) - set(pb))
        self.assertLessEqual(difference, pa)

        intersection = pa & pb
        self.assertEqual(len(intersection), len(set(intersection)))
        self.assertEqual(set(intersection), set(pa) & set(pb))
        self.assertLessEqual(intersection, pa)
        self.assertLessEqual(intersection, pb)

        union = pa | pb
        self.assertEqual(len(union), len(set(union)))
        self.assertEqual(set(union), set(pa) | set(pb))
        self.assertGreaterEqual(union, pa)
        self.assertGreaterEqual(union, pb)

        ps = pa
        ms = self.env["ir.ui.menu"].search([])
        self.assertNotEqual(ps._name, ms._name)
        self.assertNotEqual(ps, ms)

        with self.assertRaisesRegex(
            TypeError,
            r"unsupported operand types in: res\.partner.* \+ 'string'",
        ):
            _ = ps + "string"
        with self.assertRaisesRegex(
            TypeError,
            r"inconsistent models in: res\.partner.* \+ ir\.ui\.menu.*",
        ):
            _ = ps + ms
        with self.assertRaisesRegex(
            TypeError,
            r"inconsistent models in: res\.partner.* - ir\.ui\.menu.*",
        ):
            _ = ps - ms
        with self.assertRaisesRegex(
            TypeError,
            r"inconsistent models in: res\.partner.* & ir\.ui\.menu.*",
        ):
            _ = ps & ms
        with self.assertRaisesRegex(
            TypeError,
            r"inconsistent models in: res\.partner.* \| ir\.ui\.menu.*",
        ):
            _ = ps | ms
        with self.assertRaises(TypeError):
            _ = ps < ms
        with self.assertRaises(TypeError):
            _ = ps <= ms
        with self.assertRaises(TypeError):
            _ = ps > ms
        with self.assertRaises(TypeError):
            _ = ps >= ms

    @mute_logger("odoo.models")
    def test_80_lazy_set_operations(self):
        pa = lazy(
            lambda: self.env["res.partner"].search(
                [("name", "ilike", "a"), ("id", "in", self.partners.ids)]
            )
        )
        pb = lazy(
            lambda: self.env["res.partner"].search(
                [("name", "ilike", "b"), ("id", "in", self.partners.ids)]
            )
        )

        self.assertTrue(pa)
        self.assertTrue(pb)
        self.assertTrue(set(pa) & set(pb))

        concat = pa + pb
        self.assertEqual(list(concat), list(pa) + list(pb))
        self.assertEqual(len(concat), len(pa) + len(pb))

        difference = pa - pb
        self.assertEqual(len(difference), len(set(difference)))
        self.assertEqual(set(difference), set(pa) - set(pb))
        self.assertLessEqual(difference, pa)

        intersection = pa & pb
        self.assertEqual(len(intersection), len(set(intersection)))
        self.assertEqual(set(intersection), set(pa) & set(pb))
        self.assertLessEqual(intersection, pa)
        self.assertLessEqual(intersection, pb)

        union = pa | pb
        self.assertEqual(len(union), len(set(union)))
        self.assertEqual(set(union), set(pa) | set(pb))
        self.assertGreaterEqual(union, pa)
        self.assertGreaterEqual(union, pb)

        ps = pa
        ms = lazy(lambda: self.env["ir.ui.menu"].search([]))
        self.assertNotEqual(ps._name, ms._name)
        self.assertNotEqual(ps, ms)

        with self.assertRaisesRegex(
            TypeError,
            r"unsupported operand types in: res\.partner.* \+ 'string'",
        ):
            _ = ps + "string"
        with self.assertRaisesRegex(
            TypeError,
            r"inconsistent models in: res\.partner.* \+ ir\.ui\.menu.*",
        ):
            _ = ps + ms
        with self.assertRaisesRegex(
            TypeError,
            r"inconsistent models in: res\.partner.* - ir\.ui\.menu.*",
        ):
            _ = ps - ms
        with self.assertRaisesRegex(
            TypeError,
            r"inconsistent models in: res\.partner.* & ir\.ui\.menu.*",
        ):
            _ = ps & ms
        with self.assertRaisesRegex(
            TypeError,
            r"inconsistent models in: res\.partner.* \| ir\.ui\.menu.*",
        ):
            _ = ps | ms
        with self.assertRaises(TypeError):
            _ = ps < ms
        with self.assertRaises(TypeError):
            _ = ps <= ms
        with self.assertRaises(TypeError):
            _ = ps > ms
        with self.assertRaises(TypeError):
            _ = ps >= ms

    @mute_logger("odoo.models")
    def test_80_filter(self):
        ps = self.partners
        companies = ps.browse([p.id for p in ps if p.is_company])

        self.assertEqual(ps.filtered(lambda p: p.is_company), companies)
        self.assertEqual(ps.filtered("is_company"), companies)

        self.assertEqual(
            ps.filtered(lambda p: p.parent_id.is_company),
            ps.filtered("parent_id.is_company"),
        )

    @mute_logger("odoo.models")
    def test_80_map(self):
        ps = self.partners
        parents = ps.browse()
        for p in ps:
            parents |= p.parent_id

        self.assertEqual(ps.mapped(lambda p: p.parent_id), parents)
        self.assertEqual(ps.mapped("parent_id"), parents)
        self.assertEqual(ps.parent_id, parents)

        self.assertEqual(
            ps.mapped(lambda p: p.parent_id.name),
            [p.parent_id.name for p in ps],
        )
        self.assertEqual(ps.mapped("parent_id.name"), [p.name for p in parents])
        self.assertEqual(ps.parent_id.mapped("name"), [p.name for p in parents])

        self.assertEqual(ps.mapped(""), ps)

    @mute_logger("odoo.models")
    def test_80_sorted(self):
        ps = self.env["res.partner"].search([("id", "in", self.partners.ids)])

        qs = ps[: len(ps) // 2] + ps[len(ps) // 2 :]
        self.assertEqual(qs.sorted().ids, ps.ids)

        by_name_ids = [p.id for p in sorted(ps, key=lambda p: p.name)]
        self.assertEqual(ps.sorted(lambda p: p.name).ids, by_name_ids)
        self.assertEqual(ps.sorted("name").ids, by_name_ids)

        by_name_ids = [p.id for p in sorted(ps, key=lambda p: p.name, reverse=True)]
        self.assertEqual(ps.sorted("name", reverse=True).ids, by_name_ids)

    def test_group_on(self):
        p0, p1, p2 = self.env["res.partner"].create(
            [
                {"name": "bob", "function": "guest"},
                {"name": "james", "function": "host"},
                {"name": "rhod", "function": "guest"},
            ]
        )
        pn = self.env["res.partner"].new({"name": "alex", "function": "host"})

        with self.subTest("Should work with mixes of db and new records"):
            self.assertEqual(
                (p0 | p1 | p2 | pn).grouped("function"),
                {"guest": p0 | p2, "host": p1 | pn},
            )
            self.assertEqual(
                (p0 | p1 | p2 | pn).grouped(lambda r: len(r.name)),
                {3: p0, 4: p2 | pn, 5: p1},
            )

        with self.subTest("Should allow cross-group prefetching"):
            byfn = (p0 | p1 | p2).grouped("function")
            self.env.invalidate_all()
            self.assertFalse(
                list(self.env.core.iter_cached_fields()),
                "ensure the cache is empty",
            )
            self.assertEqual(byfn["guest"].mapped("name"), ["bob", "rhod"])
            with self.assertQueries([]):
                _ = byfn["host"].name
