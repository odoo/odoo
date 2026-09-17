import random

from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.orm._recordset import is_search_overridden
from odoo.orm.domain import Domain
from odoo.orm.fields.relational._base import PENDING_SCOPE_KEY
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestX2manyCacheScope(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env,
            login="scope_x2many",
            groups="base.group_user,base.group_partner_manager",
        )
        cls.parent = cls.env["res.partner"].create({"name": "scope parent"})
        cls.visible, cls.hidden = cls.env["res.partner"].create(
            [
                {"name": "scope visible", "parent_id": cls.parent.id},
                {"name": "scope hidden", "parent_id": cls.parent.id},
            ]
        )
        cls.env["ir.rule"].create(
            {
                "name": "scope: no hidden partners",
                "model_id": cls.env["ir.model"]._get_id("res.partner"),
                "domain_force": "[('name', 'not like', 'scope hidden')]",
                "groups": [Command.link(cls.env.ref("base.group_user").id)],
            }
        )
        cls.env.invalidate_all()

    def _as_user(self):
        return self.parent.with_user(self.user)

    def test_a_sudo_read_does_not_hand_the_user_the_hidden_child(self):
        self.assertEqual(self.parent.sudo().child_ids, self.visible | self.hidden)
        self.assertEqual(self._as_user().child_ids, self.visible)

    def test_a_user_read_does_not_starve_the_superuser(self):
        self.assertEqual(self._as_user().child_ids, self.visible)
        self.assertEqual(self.parent.sudo().child_ids, self.visible | self.hidden)

    def test_a_write_in_one_scope_is_seen_by_the_other(self):
        self.assertEqual(self._as_user().child_ids, self.visible)
        self.assertEqual(self.parent.sudo().child_ids, self.visible | self.hidden)
        added = self.env["res.partner"].create({"name": "scope added"})
        self.parent.sudo().write({"child_ids": [Command.link(added.id)]})
        self.assertEqual(
            self.parent.sudo().child_ids, self.visible | self.hidden | added
        )
        self.assertEqual(self._as_user().child_ids, self.visible | added)
        self._as_user().write({"child_ids": [Command.unlink(added.id)]})
        self.assertEqual(self.parent.sudo().child_ids, self.visible | self.hidden)
        self.assertEqual(self._as_user().child_ids, self.visible)

    def test_an_inverse_write_under_sudo_reaches_a_user_slot_filled_before(self):
        self.assertEqual(self._as_user().child_ids, self.visible)
        added = (
            self.env["res.partner"]
            .sudo()
            .create({"name": "scope added by parent_id", "parent_id": self.parent.id})
        )
        self.assertEqual(self._as_user().child_ids, self.visible | added)
        added.sudo().write({"parent_id": False})
        self.assertEqual(self._as_user().child_ids, self.visible)

    def test_a_user_write_serves_the_superuser_when_no_rule_filters_the_comodel(self):
        tag = self.env["res.partner.tag"].create({"name": "scope tag"})
        self.visible.with_user(self.user).write({"tag_ids": [Command.set(tag.ids)]})
        with self.assertQueryCount(0):
            self.assertEqual(self.visible.sudo().tag_ids, tag)

    def test_a_user_write_leaves_the_superuser_to_fetch_when_a_rule_filters(self):
        self.assertEqual(self.parent.sudo().child_ids, self.visible | self.hidden)
        self._as_user().write({"child_ids": [Command.unlink(self.visible.id)]})
        self.assertEqual(self._as_user().child_ids, self.env["res.partner"])
        self.assertEqual(self.parent.sudo().child_ids, self.hidden)

    def test_a_user_read_serves_the_superuser_when_no_rule_filters_the_comodel(self):
        tag = self.env["res.partner.tag"].create({"name": "scope read tag"})
        self.visible.write({"tag_ids": [Command.set(tag.ids)]})
        self.env.invalidate_all()
        self.assertEqual(self.visible.with_user(self.user).tag_ids, tag)
        with self.assertQueryCount(0):
            self.assertEqual(self.visible.sudo().tag_ids, tag)

    def test_a_record_created_by_a_user_serves_the_superuser_its_empty_x2many(self):
        created = (
            self.env["res.partner"]
            .with_user(self.user)
            .create({"name": "scope created"})
        )
        with self.assertQueryCount(0):
            self.assertFalse(created.sudo().child_ids)


@tagged("post_install", "-at_install")
class TestX2manyScopeKey(TransactionCase):
    def test_the_scope_keys_a_context_naming_a_company_the_user_just_lost(self):
        company_a = self.env.company
        company_b = self.env["res.company"].create({"name": "scope key B"})
        user = new_test_user(
            self.env,
            login="scope_key",
            groups="base.group_user",
            company_ids=[Command.set((company_a | company_b).ids)],
        )
        allowed = [company_a.id, company_b.id]
        env = self.env(user=user, context={"allowed_company_ids": allowed})

        user.sudo().company_ids = [Command.set(company_a.ids)]

        self.assertEqual(env._access_scope(), (user.id, tuple(sorted(allowed))))
        with self.assertRaises(AccessError):
            env.companies

    def test_a_write_evicts_a_scope_whose_user_lost_a_company(self):
        company_a = self.env.company
        company_b = self.env["res.company"].create(
            {"name": "scope evict B", "parent_id": company_a.id}
        )
        user = new_test_user(
            self.env,
            login="scope_evict",
            groups="base.group_user",
            company_ids=[Command.set((company_a | company_b).ids)],
        )
        self.env["ir.rule"].create(
            {
                "name": "scope evict: companies by name",
                "model_id": self.env["ir.model"]._get_id("res.company"),
                "domain_force": "[('name', '!=', False)]",
                "groups": [Command.link(self.env.ref("base.group_user").id)],
            }
        )
        allowed = [company_a.id, company_b.id]
        env = self.env(user=user, context={"allowed_company_ids": allowed})
        self.assertIn(company_b, company_a.with_env(env).child_ids)

        field = self.env["res.company"]._fields["child_ids"]
        (user_key,) = [
            key
            for key, slot in self.env.core.iter_context_caches(field)
            if slot
            and key != PENDING_SCOPE_KEY
            and not field._is_superuser_scope(self.env, key)
        ]

        user.sudo().company_ids = [Command.set(company_a.ids)]
        self.env.registry.clear_cache()

        self.assertTrue(field._scope_reads_through(self.env, user_key, {"name"}))


@tagged("post_install", "-at_install")
class TestX2manyScopeInvariant(TransactionCase):
    """The DB-free walk of odoo/orm/tests/test_x2many_scope_invariant_dbfree.py
    against PostgreSQL: after every step of a random sequence of reads and
    writes by a user and the superuser, every scope's x2many slot equals what
    that scope's search returns, or is absent. A user never writes the field
    the rule tests (`name`), the one stated exception of the invariant."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env,
            login="scope_walk",
            groups="base.group_user,base.group_partner_manager",
        )
        for model, hidden in (
            ("res.partner", "walk hidden"),
            ("res.partner.tag", "walk hidden"),
        ):
            cls.env["ir.rule"].create(
                {
                    "name": f"walk: no hidden {model}",
                    "model_id": cls.env["ir.model"]._get_id(model),
                    "domain_force": f"[('name', 'not like', '{hidden}')]",
                    "groups": [Command.link(cls.env.ref("base.group_user").id)],
                }
            )

    def _scopes(self):
        return {"sudo": self.env, "user": self.env(user=self.user.id, su=False)}

    def _truth(self, scope_env, field, record_id, inverse):
        comodel = scope_env[field.comodel_name].sudo()
        host = comodel.env[field.model_name].browse(record_id)
        domain = field.get_comodel_domain(host) & Domain(inverse, "in", [record_id])
        related = comodel.browse(
            comodel._search(domain, order=comodel._order, active_test=False)
        )
        if not scope_env.su:
            rule = scope_env.registry.access_policy.record_domain(
                scope_env, field.comodel_name, "read"
            )
            related = related.filtered_domain(rule)
        return related._ids

    def _check(self, parents, log):
        self.env.flush_all()
        fields_ = (
            (parents._fields["child_ids"], "parent_id"),
            (parents._fields["tag_ids"], "partner_ids"),
        )
        for field, inverse in fields_:
            for key, slot in list(self.env.core.iter_context_caches(field)):
                if key == PENDING_SCOPE_KEY:
                    continue
                for name, scope_env in self._scopes().items():
                    if scope_env.get_cache_key(field) != key:
                        continue
                    for parent_id in parents._ids:
                        if parent_id not in slot:
                            continue
                        held = slot[parent_id]
                        truth = self._truth(scope_env, field, parent_id, inverse)
                        why = (
                            f"{name}'s slot of {field} for {parent_id}; after:\n  "
                            + "\n  ".join(log)
                        )
                        # membership only: this walk renames children, and a
                        # rename moves a member in `complete_name` order without
                        # re-sorting the slots that hold it (the invariant's
                        # order clause dates from the slot's last fill); the
                        # DB-free walk, which rewrites no order key, holds order
                        self.assertEqual(set(held), set(truth), why)

    def _walk(self, seed, steps=40):
        rng = random.Random(seed)
        log = []
        Partner = self.env["res.partner"]
        parents = Partner.create([{"name": f"walk parent {i}"} for i in range(3)])
        tags = self.env["res.partner.tag"].create(
            [
                {"name": f"walk tag {i}" if i < 3 else "walk hidden tag"}
                for i in range(4)
            ]
        )
        Partner.create(
            [
                {
                    "name": "walk hidden child" if i == 0 else f"walk child {i}",
                    "parent_id": p.id,
                }
                for i, p in enumerate(parents)
            ]
        )
        self.env.invalidate_all()
        ops = [
            "read_children",
            "read_tags",
            "create_child",
            "move_child",
            "unlink_child",
            "set_children",
            "link_tag",
            "unlink_tag",
            "set_tags",
            "hide_child",
            "invalidate",
        ]
        for step in range(steps):
            name, scope_env = rng.choice(list(self._scopes().items()))
            parent = parents[rng.randrange(len(parents))].with_env(scope_env)
            op = rng.choice(ops)
            log.append(f"{step}: {name} {op} on {parent.name}")
            try:
                self._apply(op, name, scope_env, parent, parents, tags, rng)
            except AccessError as exc:
                log[-1] += f" (denied: {exc})"
            self._check(parents, log)

    def _apply(self, op, name, scope_env, parent, parents, tags, rng):
        def children_of(parent):
            return scope_env["res.partner"].search([("parent_id", "=", parent.id)])

        match op:
            case "read_children":
                _ = parent.child_ids
            case "read_tags":
                _ = parent.tag_ids
            case "create_child":
                hidden = name == "sudo" and rng.random() < 0.3
                scope_env["res.partner"].create(
                    {
                        "name": "walk hidden child"
                        if hidden
                        else f"walk child {rng.random()}",
                        "parent_id": parent.id,
                    }
                )
            case "move_child":
                if child := children_of(parent)[:1]:
                    child.write({"parent_id": parents[rng.randrange(len(parents))].id})
            case "unlink_child":
                if child := children_of(parent)[:1]:
                    child.unlink()
            case "set_children":
                keep = children_of(parent).filtered(lambda _c: rng.random() < 0.5)
                parent.write({"child_ids": [Command.set(keep.ids)]})
            case "link_tag" | "unlink_tag":
                tag = tags[rng.randrange(len(tags))]
                if name == "sudo" or "hidden" not in tag.name:
                    command = Command.link if op == "link_tag" else Command.unlink
                    parent.write({"tag_ids": [command(tag.id)]})
            case "set_tags":
                pool = (
                    tags
                    if name == "sudo"
                    else tags.filtered(lambda t: "hidden" not in t.name)
                )
                chosen = pool.filtered(lambda _t: rng.random() < 0.5)
                parent.write({"tag_ids": [Command.set(chosen.ids)]})
            case "hide_child":
                if name == "sudo" and (child := children_of(parent)[:1]):
                    child.write(
                        {
                            "name": "walk hidden child"
                            if "hidden" not in child.name
                            else "walk child again"
                        }
                    )
            case "invalidate":
                self.env.invalidate_all()

    def test_every_scope_slot_equals_its_search_or_is_absent(self):
        for seed in range(8):
            with self.subTest(seed=seed), self.env.cr.savepoint():
                self._walk(seed)


@tagged("post_install", "-at_install")
class TestSearchVisibilityFields(TransactionCase):
    def test_every_declared_visibility_field_exists_on_its_model(self):
        # a _search override that narrows by code names the fields it reads;
        # a name no field carries would never evict a slot
        declared = {
            name: cls._search_visibility_fields
            for name, cls in self.env.registry.items()
            if cls._search_visibility_fields is not None
        }
        self.assertTrue(declared, "no model declares _search_visibility_fields")
        for name, fields_ in declared.items():
            with self.subTest(model=name):
                self.assertEqual(
                    [f for f in fields_ if f not in self.env[name]._fields],
                    [],
                    f"{name}._search_visibility_fields names fields it lacks",
                )

    def test_every_search_override_declares_its_visibility_fields(self):
        # None is the conservative reading -- every write refetches -- and a
        # choice nobody made; an override says what its search reads, or ()
        undeclared = sorted(
            name
            for name, cls in self.env.registry.items()
            if is_search_overridden(cls) and cls._search_visibility_fields is None
        )
        self.assertEqual(
            undeclared, [], "_search overrides without _search_visibility_fields"
        )
