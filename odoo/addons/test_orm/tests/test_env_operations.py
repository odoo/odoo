"""Tests for environment manipulation operations.

The EnvironmentMixin provides methods for switching user, company, context,
and superuser mode. The Environment itself is the central ORM context object
that ties together cursor, user, and context. These methods are used
pervasively in business logic but had no dedicated tests.
"""

from odoo.tests.common import TransactionCase


class TestSudo(TransactionCase):
    """Test sudo() for superuser mode toggling."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Category = cls.env["test_orm.category"]
        cls.cat = cls.Category.create({"name": "Sudo Cat"})
        # Use a non-SUPERUSER user so sudo(False) can actually disable su.
        # Environment.__new__ forces su=True when uid == SUPERUSER_ID.
        cls.admin_user = cls.env.ref("base.user_admin")

    def test_sudo_enables_su(self):
        """sudo() enables superuser mode."""
        record = self.cat.with_user(self.admin_user).sudo()
        self.assertTrue(record.env.su)

    def test_sudo_preserves_user(self):
        """sudo() does not change the user — it only bypasses access rights."""
        record = self.cat.with_user(self.admin_user)
        sudo_record = record.sudo()
        self.assertEqual(sudo_record.env.uid, self.admin_user.id)
        self.assertTrue(sudo_record.env.su)

    def test_sudo_false_reverts(self):
        """sudo(False) disables superuser mode on a non-SUPERUSER_ID user."""
        # with_user sets su=False; sudo() then enables it
        record = self.cat.with_user(self.admin_user).sudo()
        self.assertTrue(record.env.su)
        record2 = record.sudo(False)
        self.assertFalse(record2.env.su)

    def test_sudo_idempotent(self):
        """sudo() on already sudo record returns same record."""
        record = self.cat.with_user(self.admin_user).sudo()
        record2 = record.sudo()
        # Should be the same object (no new environment created)
        self.assertIs(record, record2)

    def test_sudo_false_idempotent(self):
        """sudo(False) on non-sudo record returns same record."""
        record = self.cat.with_user(self.admin_user)
        self.assertFalse(record.env.su)
        record2 = record.sudo(False)
        self.assertIs(record, record2)


class TestWithUser(TransactionCase):
    """Test with_user() for user switching."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Use existing system users to avoid res_users_settings creation issues
        cls.admin_user = cls.env.ref("base.user_admin")
        cls.cat = cls.env["test_orm.category"].create({"name": "User Cat"})

    def test_with_user_changes_uid(self):
        """with_user() changes the environment uid."""
        record = self.cat.with_user(self.admin_user)
        self.assertEqual(record.env.uid, self.admin_user.id)

    def test_with_user_disables_su(self):
        """with_user() disables superuser mode (unless superuser)."""
        record = self.cat.sudo().with_user(self.admin_user)
        self.assertFalse(record.env.su)

    def test_with_user_preserves_records(self):
        """Same records, different user."""
        record = self.cat.with_user(self.admin_user)
        self.assertEqual(record.id, self.cat.id)
        self.assertEqual(record.name, "User Cat")

    def test_with_user_false_noop(self):
        """with_user(False) is a no-op."""
        record = self.cat.with_user(False)
        self.assertEqual(record.env.uid, self.cat.env.uid)

    def test_with_user_chain(self):
        """Chaining with_user uses the last user."""
        # Switch to admin, then back to the current user
        current_user = self.env.user
        record = self.cat.with_user(self.admin_user).with_user(current_user)
        self.assertEqual(record.env.uid, current_user.id)


class TestWithContext(TransactionCase):
    """Test with_context() for context manipulation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cat = cls.env["test_orm.category"].create({"name": "Ctx Cat"})

    def test_with_context_add(self):
        """with_context(key=val) adds to existing context."""
        record = self.cat.with_context(custom_key="custom_value")
        self.assertEqual(record.env.context.get("custom_key"), "custom_value")

    def test_with_context_preserves_existing(self):
        """Adding context preserves existing keys."""
        record = self.cat.with_context(key1="v1")
        record2 = record.with_context(key2="v2")
        self.assertEqual(record2.env.context.get("key1"), "v1")
        self.assertEqual(record2.env.context.get("key2"), "v2")

    def test_with_context_replace(self):
        """with_context({}, key=val) replaces the entire context."""
        record = self.cat.with_context(key1="v1")
        record2 = record.with_context({}, key2="v2")
        self.assertNotIn("key1", record2.env.context)
        self.assertEqual(record2.env.context.get("key2"), "v2")

    def test_with_context_preserves_records(self):
        """Same records with different context."""
        record = self.cat.with_context(custom=True)
        self.assertEqual(record.id, self.cat.id)
        self.assertEqual(record.name, "Ctx Cat")

    def test_with_context_preserves_allowed_company_ids(self):
        """When replacing context, allowed_company_ids is preserved."""
        company_ids = [1, 2, 3]
        record = self.cat.with_context(allowed_company_ids=company_ids)
        # Replace context but don't set allowed_company_ids — it should be kept
        record2 = record.with_context({}, custom=True)
        self.assertEqual(record2.env.context.get("allowed_company_ids"), company_ids)

    def test_with_context_override_value(self):
        """Overriding an existing context key."""
        record = self.cat.with_context(key="old")
        record2 = record.with_context(key="new")
        self.assertEqual(record2.env.context.get("key"), "new")


class TestWithCompany(TransactionCase):
    """Test with_company() for company switching."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cat = cls.env["test_orm.category"].create({"name": "Company Cat"})
        cls.main_company = cls.env.ref("base.main_company")

    def test_with_company(self):
        """with_company() sets allowed_company_ids in context."""
        record = self.cat.with_company(self.main_company)
        allowed = record.env.context.get("allowed_company_ids", [])
        self.assertIn(self.main_company.id, allowed)
        self.assertEqual(allowed[0], self.main_company.id)

    def test_with_company_false_noop(self):
        """with_company(False) is a no-op."""
        record = self.cat.with_company(False)
        self.assertEqual(record.env.context, self.cat.env.context)

    def test_with_company_idempotent(self):
        """Setting same company again is idempotent."""
        record = self.cat.with_company(self.main_company)
        record2 = record.with_company(self.main_company)
        self.assertIs(record, record2)


class TestWithPrefetch(TransactionCase):
    """Test with_prefetch() for controlling prefetch groups."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Category = cls.env["test_orm.category"]
        cls.cats = Category.create([{"name": f"PF{i}"} for i in range(5)])

    def test_with_prefetch_default(self):
        """with_prefetch() without args uses self._ids."""
        subset = self.cats[:2]
        record = subset.with_prefetch()
        self.assertEqual(tuple(record._prefetch_ids), subset._ids)

    def test_with_prefetch_custom(self):
        """with_prefetch(ids) sets custom prefetch group."""
        subset = self.cats[:2]
        all_ids = self.cats._ids
        record = subset.with_prefetch(all_ids)
        self.assertEqual(record._prefetch_ids, all_ids)
        # Records are the same
        self.assertEqual(record._ids, subset._ids)

    def test_with_prefetch_preserves_env(self):
        """with_prefetch preserves the environment."""
        record = self.cats[:1].with_prefetch(self.cats._ids)
        self.assertEqual(record.env, self.cats.env)


class TestEnsureOne(TransactionCase):
    """Test ensure_one() singleton validation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Category = cls.env["test_orm.category"]
        cls.cat = Category.create({"name": "Single Cat"})
        cls.cats = Category.create([{"name": f"Multi{i}"} for i in range(3)])

    def test_ensure_one_singleton(self):
        """ensure_one() passes for singleton, returns self."""
        result = self.cat.ensure_one()
        self.assertIs(result, self.cat)

    def test_ensure_one_empty(self):
        """ensure_one() raises ValueError for empty recordset."""
        empty = self.env["test_orm.category"]
        with self.assertRaises(ValueError):
            empty.ensure_one()

    def test_ensure_one_multi(self):
        """ensure_one() raises ValueError for multi-record recordset."""
        with self.assertRaises(ValueError):
            self.cats.ensure_one()


class TestEnvironmentProperties(TransactionCase):
    """Test environment properties and access patterns."""

    def test_env_user(self):
        """env.user returns the current user as a record."""
        user = self.env.user
        self.assertEqual(user._name, "res.users")
        self.assertEqual(user.id, self.env.uid)

    def test_env_company(self):
        """env.company returns the current company."""
        company = self.env.company
        self.assertEqual(company._name, "res.company")
        self.assertTrue(company)

    def test_env_registry_access(self):
        """env[model_name] returns an empty recordset of that model."""
        Category = self.env["test_orm.category"]
        self.assertEqual(Category._name, "test_orm.category")
        self.assertFalse(Category)  # empty recordset

    def test_env_cr(self):
        """env.cr is the database cursor."""
        self.assertIsNotNone(self.env.cr)

    def test_env_uid(self):
        """env.uid is the current user id."""
        self.assertIsInstance(self.env.uid, int)
        self.assertTrue(self.env.uid > 0)


class TestExists(TransactionCase):
    """Test exists() for filtering out deleted records."""

    def test_exists_all_present(self):
        """exists() returns all records when all exist."""
        cats = self.env["test_orm.category"].create(
            [{"name": f"Exists{i}"} for i in range(3)]
        )
        result = cats.exists()
        self.assertEqual(result, cats)

    def test_exists_filters_deleted(self):
        """exists() filters out deleted records."""
        cat1 = self.env["test_orm.category"].create({"name": "Keep"})
        cat2 = self.env["test_orm.category"].create({"name": "Delete"})
        both = cat1 | cat2
        cat2.unlink()
        result = both.exists()
        self.assertEqual(result, cat1)

    def test_exists_empty(self):
        """exists() on empty recordset returns empty."""
        empty = self.env["test_orm.category"]
        result = empty.exists()
        self.assertFalse(result)

    def test_exists_all_deleted(self):
        """exists() returns empty when all records are deleted."""
        cat = self.env["test_orm.category"].create({"name": "Gone"})
        cat.unlink()
        result = cat.exists()
        self.assertFalse(result)


class TestNewRecords(TransactionCase):
    """Test new() for creating virtual records and _origin property."""

    def test_new_basic(self):
        """new() creates a virtual record not in DB."""
        Category = self.env["test_orm.category"]
        record = Category.new({"name": "Virtual"})
        self.assertEqual(record.name, "Virtual")
        self.assertFalse(record.id)  # NewId is falsy

    def test_new_with_origin(self):
        """new(origin=record) tracks the original DB record."""
        cat = self.env["test_orm.category"].create({"name": "Original"})
        virtual = self.env["test_orm.category"].new({"name": "Modified"}, origin=cat)
        self.assertFalse(virtual.id)  # Still a new record
        self.assertEqual(virtual._origin, cat)

    def test_new_with_ref(self):
        """new(ref=value) creates trackable virtual records."""
        Category = self.env["test_orm.category"]
        rec1 = Category.new({"name": "A"}, ref="ref1")
        rec2 = Category.new({"name": "B"}, ref="ref1")
        # Same ref means equal NewIds
        self.assertEqual(rec1.id, rec2.id)

    def test_origin_real_records(self):
        """_origin on real records returns self."""
        cat = self.env["test_orm.category"].create({"name": "Real"})
        self.assertEqual(cat._origin, cat)
