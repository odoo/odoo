"""ORM Hot Path Contract Tests.

Focused regression tests for the implicit contracts that ORM hot paths
depend on.  When optimizing Field.__get__, _read_format, mapped/filtered/
sorted/grouped, write→flush→recompute, or create→cache, run this suite
FIRST (~5-10s) to catch contract violations before the full 800+ test run.

Each test class isolates one contract family.  Tests are deliberately
simple — they don't test business logic, they test that the fast path
produces the same result as the reference path.

Run with::

    ./core/odoo-bin -c ./conf/odoo.conf -d test_db \
        --test-tags 'hotpath_contracts' -u test_orm --stop-after-init --workers=0

Contract families:
    1. Field.__get__ — ACL, singleton, recompute, cache, fetch, PENDING
    2. _read_format — Phase 1 (scalar) vs Phase 2 equivalence
    3. Traversal — mapped/filtered/sorted/grouped fast path vs standard
    4. write→flush — dirty tracking, flush correctness, deferred UPDATE
    5. create→cache — cache population, PENDING for computed, modified()
    6. Precondition API — ensure_computed, ensure_access, read_cache
"""

from odoo.fields import Command
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.misc import PENDING, SENTINEL


@tagged("-standard", "hotpath_contracts")
class TestFieldGetContracts(TransactionCase):
    """Contract: Field.__get__ must return identical results whether using
    the optimized closure path (_make_scalar_get) or the base Field.__get__.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Mixed = cls.env["test_orm.mixed"]

    def test_scalar_types_cache_hit(self):
        """All scalar types return correct values from cache."""
        record = self.Mixed.create(
            {
                "foo": "hello",
                "truth": True,
                "count": 42,
                "number": 3.14,
                "date": "2025-01-15",
                "moment": "2025-01-15 10:30:00",
                "lang": "en_US",
            }
        )
        # Flush + re-fetch to ensure values go through full roundtrip
        self.env.flush_all()
        record.invalidate_recordset()
        record.fetch(["foo", "truth", "count", "number", "date", "moment", "lang"])

        # Each field type exercises a different _make_scalar_get closure
        self.assertEqual(record.foo, "hello")
        self.assertIs(record.truth, True)
        self.assertEqual(record.count, 42)
        self.assertAlmostEqual(record.number, 3.14, places=2)
        self.assertEqual(str(record.date), "2025-01-15")
        self.assertEqual(record.lang, "en_US")

    def test_scalar_none_to_falsy(self):
        """None cache values convert to type-appropriate falsy defaults."""
        record = self.Mixed.create({})
        self.env.flush_all()
        record.invalidate_recordset()
        record.fetch(["foo", "truth", "count", "number", "date", "moment"])

        # Each type has a specific falsy default:
        #   Char → False, Boolean → False, Integer → 0,
        #   Float → 0.0, Date → False, Datetime → False
        self.assertIs(record.foo, False)
        self.assertIs(record.truth, False)
        self.assertEqual(record.count, 0)
        self.assertEqual(record.number, 3.14)  # has default
        self.assertIs(record.date, False)
        self.assertIs(record.moment, False)

    def test_empty_recordset_returns_falsy(self):
        """__get__ on empty recordset returns type-appropriate falsy value."""
        empty = self.Mixed.browse()
        self.assertIs(empty.foo, False)
        self.assertIs(empty.truth, False)
        self.assertEqual(empty.count, 0)
        self.assertIs(empty.date, False)

    def test_multi_record_raises(self):
        """__get__ on multi-record set raises ValueError (ensure_one)."""
        r1 = self.Mixed.create({"foo": "a"})
        r2 = self.Mixed.create({"foo": "b"})
        multi = r1 | r2
        with self.assertRaises(ValueError):
            _ = multi.foo

    def test_many2one_returns_recordset(self):
        """Many2one __get__ returns a recordset, not a raw ID."""
        record = self.Mixed.create({})
        partner = record.currency_id
        # Must be a recordset (or falsy), never an int
        if partner:
            self.assertTrue(hasattr(partner, "_ids"))
            self.assertTrue(hasattr(partner, "env"))


@tagged("-standard", "hotpath_contracts")
class TestFieldGetPending(TransactionCase):
    """Contract: PENDING sentinel must never leak to callers of __get__."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Move = cls.env["test_orm.move"]

    def test_stored_computed_after_create(self):
        """Stored computed fields return computed value, not PENDING."""
        move = self.Move.create({})
        self.env["test_orm.move_line"].create(
            {
                "move_id": move.id,
                "quantity": 10,
            }
        )
        # quantity is stored computed from line_ids.quantity
        # After create + recompute, must return actual value
        self.assertEqual(move.quantity, 10)
        # Verify it's not PENDING
        self.assertIsNot(move.quantity, PENDING)

    def test_pending_evicted_on_read(self):
        """If PENDING is in cache, __get__ evicts it and fetches real value."""
        move = self.Move.create({})
        self.env.flush_all()

        # Manually inject PENDING to simulate stale state
        field = self.Move._fields["quantity"]
        field_cache = field._get_cache(self.env)
        field_cache[move.id] = PENDING

        # __get__ must handle PENDING — either recompute or fetch, never return it
        value = move.quantity
        self.assertIsNot(value, PENDING)
        self.assertIsInstance(value, int)


@tagged("-standard", "hotpath_contracts")
class TestReadFormatContracts(TransactionCase):
    """Contract: _read_format Phase 1 (scalar fast path) must produce
    identical output to Phase 2 (full singleton path) for the same data.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Mixed = cls.env["test_orm.mixed"]

    def _reference_read_format(self, records, fnames):
        """Simulate Phase 2 (singleton) path for all fields."""
        result = []
        for record in records:
            vals = {"id": record.id}
            for fname in fnames:
                field = records._fields[fname]
                vals[fname] = field.convert_to_read(record[fname], record, False)
            result.append(vals)
        return result

    def test_scalar_phase1_matches_reference(self):
        """Phase 1 scalar path matches reference singleton path."""
        records = self.Mixed.browse()
        for i in range(5):
            records |= self.Mixed.create(
                {
                    "foo": f"name_{i}",
                    "truth": i % 2 == 0,
                    "count": i * 10,
                    "number": i * 1.5,
                    "date": f"2025-01-{15 + i:02d}",
                    "moment": f"2025-01-{15 + i:02d} 10:30:00",
                }
            )

        self.env.flush_all()
        records.invalidate_recordset()
        records.fetch(["foo", "truth", "count", "number", "date", "moment"])

        scalar_fnames = ["foo", "truth", "count", "number", "date", "moment"]

        # Get fast path result
        fast_result = records._read_format(fnames=scalar_fnames, load=None)
        # Get reference result
        ref_result = self._reference_read_format(records, scalar_fnames)

        self.assertEqual(len(fast_result), len(ref_result))
        for fast, ref in zip(fast_result, ref_result, strict=False):
            self.assertEqual(fast["id"], ref["id"])
            for fname in scalar_fnames:
                self.assertEqual(
                    fast[fname],
                    ref[fname],
                    f"Mismatch on {fname}: fast={fast[fname]!r} vs ref={ref[fname]!r} "
                    f"(record id={fast['id']})",
                )

    def test_none_values_phase1(self):
        """Phase 1 correctly converts None to type-appropriate falsy values."""
        record = self.Mixed.create({})
        self.env.flush_all()
        record.invalidate_recordset()
        record.fetch(["foo", "truth", "count"])

        result = record._read_format(fnames=["foo", "truth", "count"], load=None)
        self.assertEqual(len(result), 1)
        vals = result[0]
        self.assertIs(vals["foo"], False)
        self.assertIs(vals["truth"], False)
        self.assertEqual(vals["count"], 0)

    def test_many2one_with_and_without_display_name(self):
        """Many2one Phase 1 fast path (load=None) vs Phase 2 (load=_classic_read)."""
        record = self.Mixed.create({})
        self.env.flush_all()
        record.invalidate_recordset()
        record.fetch(["currency_id"])

        # load=None: Many2one should return raw ID (int or False)
        result_no_load = record._read_format(fnames=["currency_id"], load=None)
        val = result_no_load[0]["currency_id"]
        self.assertTrue(val is False or isinstance(val, int))

        # load=_classic_read: Many2one should return (id, display_name) or False
        result_classic = record._read_format(
            fnames=["currency_id"], load="_classic_read"
        )
        val = result_classic[0]["currency_id"]
        if val:
            self.assertIsInstance(val, (list, tuple))
            self.assertEqual(len(val), 2)


@tagged("-standard", "hotpath_contracts")
class TestTraversalContracts(TransactionCase):
    """Contract: mapped/filtered/sorted/grouped fast paths must produce
    identical results to the standard (non-fast) code path.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Msg = cls.env["test_orm.message"]
        cls.Disc = cls.env["test_orm.discussion"]

    def setUp(self):
        super().setUp()
        # Discussion requires author in participants (constraint on message)
        self.disc = self.Disc.create(
            {
                "name": "Test Discussion",
                "participants": [Command.link(self.env.uid)],
            }
        )
        self.messages = self.Msg.browse()
        for i in range(10):
            self.messages |= self.Msg.create(
                {
                    "discussion": self.disc.id,
                    "body": f"body_{i}",
                    "important": i % 3 == 0,
                    "priority": i,
                }
            )
        self.env.flush_all()

    def test_mapped_scalar_fast_path(self):
        """mapped('field') fast path matches lambda path for scalars."""
        fast = self.messages.mapped("priority")
        standard = [rec.priority for rec in self.messages]
        self.assertEqual(fast, standard)

    def test_mapped_scalar_with_none(self):
        """mapped('field') handles None/False values correctly."""
        # Create message with no body (body=False)
        msg = self.Msg.create({"discussion": self.disc.id, "body": False})
        records = self.messages | msg
        fast = records.mapped("body")
        standard = [rec.body for rec in records]
        self.assertEqual(fast, standard)

    def test_mapped_relational(self):
        """mapped('m2o_field') returns a recordset for relational fields."""
        result = self.messages.mapped("discussion")
        self.assertTrue(hasattr(result, "_ids"))
        self.assertIn(self.disc.id, result.ids)

    def test_filtered_scalar_fast_path(self):
        """filtered('field') fast path matches lambda path."""
        fast = self.messages.filtered("important")
        standard = self.messages.filtered(lambda r: r.important)
        self.assertEqual(fast._ids, standard._ids)

    def test_filtered_falsy_field(self):
        """filtered('field') correctly excludes falsy values."""
        # body is set for all, so filter on it
        with_body = self.messages.filtered("body")
        self.assertEqual(len(with_body), len(self.messages))

        # Create one without body (set author explicitly to satisfy constraint)
        no_body = self.Msg.create({"discussion": self.disc.id, "body": False})
        all_msgs = self.messages | no_body
        filtered = all_msgs.filtered("body")
        self.assertNotIn(no_body.id, filtered.ids)

    def test_sorted_single_field(self):
        """sorted('field') fast path matches standard sorted."""
        fast = self.messages.sorted("priority")
        standard = self.messages.sorted(key=lambda r: r.priority)
        self.assertEqual(fast._ids, standard._ids)

    def test_sorted_descending(self):
        """sorted('field DESC') produces reversed order."""
        asc = self.messages.sorted("priority")
        desc = self.messages.sorted("priority DESC")
        self.assertEqual(asc._ids, tuple(reversed(desc._ids)))

    def test_sorted_with_nulls(self):
        """sorted() handles None values without crashing."""
        # Create message with no body (Char field → False in cache)
        msg = self.Msg.create({"discussion": self.disc.id})
        records = self.messages | msg
        # Must not raise — None handling in ReversibleComparator
        result = records.sorted("body")
        self.assertEqual(len(result), len(records))

    def test_sorted_multi_field(self):
        """sorted('field1, field2') produces correct composite order."""
        result = self.messages.sorted("important DESC, priority")
        # All important=True should come first (DESC), then sorted by priority ASC
        important_ids = [r.id for r in result if r.important]
        [r.id for r in result if not r.important]
        # Important ones should be at the start
        all_ids = list(result._ids)
        self.assertEqual(all_ids[: len(important_ids)], important_ids)

    def test_grouped_scalar(self):
        """grouped('field') fast path matches standard grouped."""
        fast = self.messages.grouped("important")
        standard = {}
        for record in self.messages:
            key = record.important
            standard.setdefault(key, self.Msg.browse())
            standard[key] = standard[key] | record

        self.assertEqual(set(fast.keys()), set(standard.keys()))
        for key in fast:
            self.assertEqual(
                fast[key]._ids,
                standard[key]._ids,
                f"Mismatch for grouped key={key!r}",
            )


@tagged("-standard", "hotpath_contracts")
class TestWriteFlushContracts(TransactionCase):
    """Contract: write() defers SQL, flush() produces correct DB state,
    and the recompute→flush convergence loop terminates correctly.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Move = cls.env["test_orm.move"]
        cls.Line = cls.env["test_orm.move_line"]

    def test_write_defers_sql(self):
        """write() marks fields dirty without executing SQL."""
        move = self.Move.create({})
        self.env.flush_all()

        # After write, value should be in cache but DB may have old value
        move.tag_repeat = 5
        self.assertEqual(move.tag_repeat, 5)  # cache updated

        # Check dirty tracking
        field = self.Move._fields["tag_repeat"]
        core = self.env._core
        self.assertTrue(core.has_dirty_field(field))

    def test_flush_writes_to_db(self):
        """flush_all() writes dirty values to database."""
        move = self.Move.create({})
        self.env.flush_all()
        move.tag_repeat = 7
        self.env.flush_all()

        # Read from DB directly to verify
        self.env.cr.execute(
            "SELECT tag_repeat FROM test_orm_move WHERE id = %s",
            (move.id,),
        )
        db_value = self.env.cr.fetchone()[0]
        self.assertEqual(db_value, 7)

    def test_recompute_triggers_on_write(self):
        """Writing to a dependency triggers recomputation of stored computed."""
        move = self.Move.create({})
        line = self.Line.create({"move_id": move.id, "quantity": 5})
        self.env.flush_all()
        self.assertEqual(move.quantity, 5)

        # Write to dependency
        line.quantity = 15
        # Stored computed field should recompute (lazily or on access)
        self.assertEqual(move.quantity, 15)

    def test_flush_convergence(self):
        """Recomputation that dirties more fields converges (no infinite loop)."""
        # test_orm.move.tag_string depends on tag_name + tag_repeat
        # tag_name is related to tag_id.name
        tag = self.env["test_orm.multi.tag"].create({"name": "X"})
        move = self.Move.create({"tag_id": tag.id, "tag_repeat": 3})
        self.env.flush_all()

        # tag_string = tag_name * tag_repeat = "XXX"
        self.assertEqual(move.tag_string, "XXX")

        # Change dependency — triggers recompute chain
        move.tag_repeat = 2
        self.env.flush_all()
        self.assertEqual(move.tag_string, "XX")

    def test_multiple_writes_batched(self):
        """Multiple writes to same record batch into single flush."""
        move = self.Move.create({})
        self.env.flush_all()

        move.tag_repeat = 1
        move.tag_repeat = 2
        move.tag_repeat = 3

        # Only final value should be flushed
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT tag_repeat FROM test_orm_move WHERE id = %s",
            (move.id,),
        )
        self.assertEqual(self.env.cr.fetchone()[0], 3)


@tagged("-standard", "hotpath_contracts")
class TestCreateCacheContracts(TransactionCase):
    """Contract: create() populates cache correctly, schedules recomputation
    for stored computed fields, and triggers modified() for all fields.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Move = cls.env["test_orm.move"]
        cls.Line = cls.env["test_orm.move_line"]

    def test_cache_populated_after_create(self):
        """Stored fields are in cache immediately after create()."""
        move = self.Move.create({"tag_repeat": 5})
        # Should be readable from cache without DB fetch
        field = self.Move._fields["tag_repeat"]
        field_cache = field._get_cache(self.env)
        self.assertIn(move.id, field_cache)
        self.assertEqual(field_cache[move.id], 5)

    def test_computed_field_available_after_create(self):
        """Stored computed fields are computable after create()."""
        move = self.Move.create({})
        self.Line.create({"move_id": move.id, "quantity": 7})
        # quantity is stored computed — should be available
        val = move.quantity
        self.assertEqual(val, 7)
        self.assertIsNot(val, PENDING)

    def test_batch_create_cache(self):
        """Batch create populates cache for all records."""
        moves = self.Move.create([{"tag_repeat": i} for i in range(5)])
        field = self.Move._fields["tag_repeat"]
        field_cache = field._get_cache(self.env)
        for move in moves:
            self.assertIn(move.id, field_cache)

    def test_create_with_relational(self):
        """create() with Many2one populates cache correctly."""
        tag = self.env["test_orm.multi.tag"].create({"name": "T"})
        move = self.Move.create({"tag_id": tag.id})

        field = self.Move._fields["tag_id"]
        field_cache = field._get_cache(self.env)
        self.assertIn(move.id, field_cache)
        # Cache stores raw ID for Many2one
        self.assertEqual(field_cache[move.id], tag.id)


@tagged("-standard", "hotpath_contracts")
class TestPreconditionAPI(TransactionCase):
    """Contract: ensure_computed(), ensure_access(), read_cache() behave
    as documented — these are the named contracts that fast paths rely on.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Move = cls.env["test_orm.move"]
        cls.Line = cls.env["test_orm.move_line"]
        cls.Mixed = cls.env["test_orm.mixed"]

    def test_ensure_computed_triggers_recompute(self):
        """ensure_computed() resolves pending recomputations."""
        move = self.Move.create({})
        self.Line.create({"move_id": move.id, "quantity": 12})

        field = self.Move._fields["quantity"]
        # Explicitly call the precondition
        field.ensure_computed(move)
        # Value should now be in cache
        field_cache = field._get_cache(self.env)
        self.assertIn(move.id, field_cache)
        self.assertEqual(field_cache[move.id], 12)
        self.assertIsNot(field_cache[move.id], PENDING)

    def test_ensure_computed_noop_for_non_computed(self):
        """ensure_computed() is a no-op for plain stored fields."""
        move = self.Move.create({"tag_repeat": 5})
        field = self.Move._fields["tag_repeat"]
        # Should not raise and should not modify cache
        field.ensure_computed(move)
        self.assertEqual(move.tag_repeat, 5)

    def test_read_cache_hit(self):
        """read_cache() returns (True, value) on cache hit."""
        record = self.Mixed.create({"foo": "test"})
        self.env.flush_all()
        record.invalidate_recordset()
        record.fetch(["foo"])

        field = self.Mixed._fields["foo"]
        hit, value = field.read_cache(record.id, self.env)
        self.assertTrue(hit)
        self.assertEqual(value, "test")

    def test_read_cache_miss(self):
        """read_cache() returns (False, SENTINEL) on cache miss."""
        record = self.Mixed.create({"foo": "test"})
        self.env.flush_all()
        record.invalidate_recordset()
        # Don't fetch — cache is empty

        field = self.Mixed._fields["foo"]
        hit, value = field.read_cache(record.id, self.env)
        self.assertFalse(hit)
        self.assertIs(value, SENTINEL)

    def test_read_cache_pending_is_miss(self):
        """read_cache() treats PENDING as a cache miss."""
        move = self.Move.create({})
        self.env.flush_all()

        field = self.Move._fields["quantity"]
        field_cache = field._get_cache(self.env)
        field_cache[move.id] = PENDING

        hit, value = field.read_cache(move.id, self.env)
        self.assertFalse(hit)
        self.assertIs(value, SENTINEL)


@tagged("-standard", "hotpath_contracts")
class TestCacheInvariant(TransactionCase):
    """Contract: cache invariants that all fast paths depend on."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Mixed = cls.env["test_orm.mixed"]

    def test_field_cache_memo_consistency(self):
        """_field_cache_memo and _get_cache return the same dict object."""
        self.Mixed.create({"foo": "test"})
        field = self.Mixed._fields["foo"]

        cache_via_method = field._get_cache(self.env)
        memo = self.env.__dict__.get("_field_cache_memo", {})
        if field in memo:
            self.assertIs(cache_via_method, memo[field])

    def test_invalidate_clears_cache(self):
        """invalidate_recordset removes values from field cache."""
        record = self.Mixed.create({"foo": "test"})
        self.env.flush_all()
        field = self.Mixed._fields["foo"]
        field_cache = field._get_cache(self.env)
        self.assertIn(record.id, field_cache)

        record.invalidate_recordset(["foo"])
        self.assertNotIn(record.id, field_cache)

    def test_flush_clears_dirty(self):
        """After flush_all(), no fields remain dirty."""
        record = self.Mixed.create({"foo": "initial"})
        self.env.flush_all()

        record.foo = "modified"
        core = self.env._core
        field = self.Mixed._fields["foo"]
        self.assertTrue(core.has_dirty_field(field))

        self.env.flush_all()
        self.assertFalse(core.has_dirty_field(field))


@tagged("-standard", "hotpath_contracts")
class TestModifiedTriggers(TransactionCase):
    """Contract: modified() correctly schedules recomputation for
    stored computed fields through the trigger tree.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Move = cls.env["test_orm.move"]
        cls.Line = cls.env["test_orm.move_line"]

    def test_o2m_dependency_triggers_parent(self):
        """Modifying a One2many child triggers recompute on parent."""
        move = self.Move.create({})
        line = self.Line.create({"move_id": move.id, "quantity": 3})
        self.env.flush_all()
        self.assertEqual(move.quantity, 3)

        # Modify child
        line.quantity = 10
        # Parent stored computed should update
        self.assertEqual(move.quantity, 10)

    def test_adding_child_triggers_parent(self):
        """Adding a new One2many child triggers recompute on parent."""
        move = self.Move.create({})
        self.Line.create({"move_id": move.id, "quantity": 5})
        self.env.flush_all()
        self.assertEqual(move.quantity, 5)

        # Add another child
        self.Line.create({"move_id": move.id, "quantity": 8})
        self.assertEqual(move.quantity, 13)

    def test_removing_child_triggers_parent(self):
        """Unlinking a One2many child triggers recompute on parent."""
        move = self.Move.create({})
        self.Line.create({"move_id": move.id, "quantity": 5})
        line2 = self.Line.create({"move_id": move.id, "quantity": 8})
        self.env.flush_all()
        self.assertEqual(move.quantity, 13)

        # Remove one child
        line2.unlink()
        self.assertEqual(move.quantity, 5)

    def test_related_field_propagation(self):
        """Writing to related field source propagates through triggers."""
        tag = self.env["test_orm.multi.tag"].create({"name": "A"})
        move = self.Move.create({"tag_id": tag.id, "tag_repeat": 2})
        self.env.flush_all()
        # tag_name is related to tag_id.name
        # tag_string depends on tag_name + tag_repeat
        self.assertEqual(move.tag_string, "AA")

        # Change the source record
        tag.name = "B"
        self.env.flush_all()
        # Must propagate: tag.name → move.tag_name → move.tag_string
        self.assertEqual(move.tag_string, "BB")


@tagged("-standard", "hotpath_contracts")
class TestReadFormatManyRecords(TransactionCase):
    """Contract: _read_format handles batch reads correctly across
    multiple records, ensuring no cross-contamination between records.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Mixed = cls.env["test_orm.mixed"]

    def test_batch_scalar_identity(self):
        """Each record in a batch gets its own values, not another record's."""
        records = self.Mixed.create(
            [{"foo": f"name_{i}", "count": i * 10} for i in range(20)]
        )
        self.env.flush_all()
        records.invalidate_recordset()
        records.fetch(["foo", "count"])

        result = records._read_format(fnames=["foo", "count"], load=None)
        self.assertEqual(len(result), 20)

        by_id = {r["id"]: r for r in result}
        for i, record in enumerate(records):
            vals = by_id[record.id]
            self.assertEqual(vals["foo"], f"name_{i}")
            self.assertEqual(vals["count"], i * 10)

    def test_mixed_cache_hit_and_miss(self):
        """_read_format handles mix of cached and uncached records."""
        records = self.Mixed.create([{"foo": f"name_{i}"} for i in range(5)])
        self.env.flush_all()

        # Invalidate only some records
        records[2].invalidate_recordset(["foo"])
        records[4].invalidate_recordset(["foo"])

        # _read_format should handle both cache hits and misses
        result = records._read_format(fnames=["foo"], load=None)
        self.assertEqual(len(result), 5)
        for i, vals in enumerate(result):
            self.assertEqual(vals["foo"], f"name_{i}")
