from odoo.tests.common import TransactionCase


class TestInvalidatePendingWrite(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]

    def _dirty_record(self):
        record = self.Partner.create({"name": "orig", "ref": "R0"})
        self.env.flush_all()
        record.write({"ref": "R1"})
        self.assertTrue(
            self.env.core.get_dirty(self.Partner._fields["ref"]),
            "precondition: the write must leave 'ref' dirty",
        )
        return record

    def _assert_refuses(self, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except ValueError as exc:
            self.assertIn("pending write", str(exc))
            return
        self.fail("invalidation with flush=False accepted a pending write")

    def test_invalidate_recordset_refuses_pending_write(self):
        record = self._dirty_record()
        self._assert_refuses(record.invalidate_recordset, ["ref"], flush=False)
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(record.ref, "R1")

    def test_invalidate_model_refuses_pending_write(self):
        record = self._dirty_record()
        self._assert_refuses(self.Partner.invalidate_model, ["ref"], flush=False)
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(record.ref, "R1")

    def test_invalidate_all_fields_refuses_pending_write(self):
        record = self._dirty_record()
        self._assert_refuses(record.invalidate_recordset, flush=False)
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(record.ref, "R1")

    def test_invalidate_other_records_is_allowed(self):
        clean = self.Partner.create({"name": "clean", "ref": "C0"})
        dirty = self._dirty_record()
        clean.invalidate_recordset(["ref"], flush=False)
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(dirty.ref, "R1")

    def test_invalidate_other_fields_is_allowed(self):
        record = self._dirty_record()
        record.invalidate_recordset(["name"], flush=False)
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(record.ref, "R1")

    def test_flush_true_stays_the_normal_path(self):
        record = self._dirty_record()
        record.invalidate_recordset(["ref"])
        self.assertEqual(record.ref, "R1")

    def test_transaction_wide_invalidate_all_keeps_pending_writes(self):
        record = self._dirty_record()
        self.env.invalidate_all(flush=False)
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(record.ref, "R1")


class TestFnameResolution(TransactionCase):
    def setUp(self):
        super().setUp()
        self.record = self.env["res.partner"].create({"name": "x"})

    def _assert_names_field_and_model(self, func, *args):
        with self.assertRaises(ValueError) as ctx:
            func(*args)
        message = str(ctx.exception)
        self.assertIn("bogus", message)
        self.assertIn("res.partner", message)

    def test_flush_model(self):
        self._assert_names_field_and_model(
            self.env["res.partner"].flush_model, ["bogus"]
        )

    def test_flush_recordset(self):
        self._assert_names_field_and_model(self.record.flush_recordset, ["bogus"])

    def test_recompute_model(self):
        self._assert_names_field_and_model(
            self.env["res.partner"]._recompute_model, ["bogus"]
        )

    def test_recompute_recordset(self):
        self._assert_names_field_and_model(self.record._recompute_recordset, ["bogus"])

    def test_invalidate_recordset_unchanged(self):
        self._assert_names_field_and_model(self.record.invalidate_recordset, ["bogus"])

    def test_invalidate_model_unchanged(self):
        self._assert_names_field_and_model(
            self.env["res.partner"].invalidate_model, ["bogus"]
        )

    def test_valid_names_still_pass(self):
        self.record.write({"ref": "R"})
        self.record.flush_recordset(["ref"])
        self.env["res.partner"].flush_model(["ref"])
        self.record._recompute_recordset(["display_name"])
        self.env["res.partner"]._recompute_model(["display_name"])


class TestInvalidateInversePendingWrite(TransactionCase):
    def _dirty_inverse(self):
        source = self.env["res.partner"].create({"name": "source"})
        target = self.env["res.partner"].create({"name": "target"})
        bank = self.env["res.partner.bank.account"].create(
            {"acc_number": "ACC-1", "partner_id": source.id}
        )
        self.env.flush_all()
        self.env.invalidate_all()

        bank.write({"partner_id": target.id})
        field = self.env["res.partner.bank.account"]._fields["partner_id"]
        self.assertIn(
            bank.id,
            self.env.core.get_dirty(field) or (),
            "precondition: the write must leave 'partner_id' dirty",
        )
        return source, bank, target

    def test_inverse_invalidation_keeps_the_pending_write(self):
        source, bank, target = self._dirty_inverse()
        source.invalidate_recordset(["bank_ids"], flush=False)

        field = self.env["res.partner.bank.account"]._fields["partner_id"]
        self.assertIn(
            bank.id,
            field._get_cache(self.env),
            "the dirty value must survive the inverse-field invalidation",
        )

        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(bank.partner_id, target)

    def test_inverse_invalidation_still_drops_clean_values(self):
        source = self.env["res.partner"].create({"name": "source"})
        target = self.env["res.partner"].create({"name": "target"})
        Bank = self.env["res.partner.bank.account"]
        bank = Bank.create({"acc_number": "ACC-1", "partner_id": source.id})
        clean = Bank.create({"acc_number": "ACC-2", "partner_id": source.id})
        self.env.flush_all()
        self.env.invalidate_all()

        field = Bank._fields["partner_id"]
        clean.partner_id
        bank.write({"partner_id": target.id})
        cache = field._get_cache(self.env)
        self.assertIn(bank.id, cache)
        self.assertIn(clean.id, cache)

        source.invalidate_recordset(["bank_ids"], flush=False)

        cache = field._get_cache(self.env)
        self.assertIn(bank.id, cache)
        self.assertNotIn(clean.id, cache)

    def test_invalidate_model_inverse_keeps_the_pending_write(self):
        _source, bank, target = self._dirty_inverse()
        self.env["res.partner"].invalidate_model(["bank_ids"], flush=False)
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(bank.partner_id, target)
