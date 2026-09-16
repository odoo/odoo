import logging

from odoo import Command
from odoo.tests.common import TransactionCase, tagged, users, warmup
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import SavepointCaseWithUserDemo

_logger = logging.getLogger(__name__)


class TestPerformance(SavepointCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._load_partners_set()

        partner3 = cls.env["res.partner"].search([("name", "=", "AnalytIQ")], limit=1)
        partner4 = cls.env["res.partner"].search(
            [("name", "=", "Urban Trends")], limit=1
        )
        partner10 = cls.env["res.partner"].search(
            [("name", "=", "Ctrl-Alt-Fix")], limit=1
        )
        partner12 = cls.env["res.partner"].search(
            [("name", "=", "Ignitive Labs")], limit=1
        )

        cls.env["test_performance.base"].create(
            [
                {
                    "name": "Object 0",
                    "value": 0,
                    "partner_id": partner3.id,
                },
                {
                    "name": "Object 1",
                    "value": 10,
                    "partner_id": partner3.id,
                },
                {
                    "name": "Object 2",
                    "value": 20,
                    "partner_id": partner4.id,
                },
                {
                    "name": "Object 3",
                    "value": 30,
                    "partner_id": partner10.id,
                },
                {
                    "name": "Object 4",
                    "value": 40,
                    "partner_id": partner12.id,
                },
            ]
        )
        cls.env.invalidate_all()

    @users("__system__", "demo")
    @warmup
    def test_read_base(self):
        records = self.env["test_performance.base"].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(__system__=2, demo=3):
            for record in records:
                record.partner_id.country_id.name

        with self.assertQueryCount(0):
            for record in records:
                record.partner_id.country_id.name

        with self.assertQueryCount(0):
            for record in records:
                record.value_pc

    @users("__system__", "demo")
    @warmup
    def test_read_base_one2many(self):
        records = self.env["test_performance.base"].search([])
        self.assertEqual(len(records), 5)

        records.write({"line_ids": [Command.create({})]})
        self.env.invalidate_all()

        with self.assertQueryCount(1):
            records.line_ids

    @users("__system__", "demo")
    @warmup
    def test_reversed_read_base(self):
        records = self.env["test_performance.base"].search([])
        self.assertEqual(len(records), 5)
        with self.assertQueryCount(__system__=1, demo=1):
            for record in reversed(records):
                record.partner_id

        with self.assertQueryCount(__system__=1, demo=1):
            for record in reversed(records):
                record.value_ctx

    @warmup
    def test_read_base_depends_context(self):
        records = self.env["test_performance.base"].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(1):
            for record in records.with_context(key=1):
                self.assertEqual(record.value_ctx, 1)

        with self.assertQueryCount(1):
            for record in records.with_context(key=2):
                self.assertEqual(record.value_ctx, 2)

        with self.assertQueryCount(1):
            for record in records:
                self.assertEqual(record.with_context(key=3).value_ctx, 3)

    def test_fetch(self):
        records = self.env["test_performance.base"].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(1):
            records.fetch(["name", "partner_id"])

        with self.assertQueryCount(0):
            records.mapped("name")
            records.mapped("partner_id")

        with self.assertQueryCount(1):
            records.mapped("value")

        with self.assertQueryCount(0):
            records.fetch(["name", "value"])

        with self.assertQueryCount(0):
            records.fetch(["id", "name", "partner_id"])

        with self.assertQueryCount(0):
            records.fetch(["id", "display_name"])

        with self.assertQueryCount(0):
            records.mapped("display_name")

            records.invalidate_recordset(["name"])

            records.fetch(["display_name"])

        with self.assertQueryCount(0):
            records.fetch(["indirect_computed_value"])

        with self.assertQueryCount(1):
            records.invalidate_recordset(
                ["value", "computed_value", "indirect_computed_value"]
            )

            records.fetch(["indirect_computed_value"])

        real_record = records[0]
        new_record_origin = records.new(origin=real_record)
        new_record_ref = records.new(ref="virtual_")
        new_record = records.new({"name": "aaa"})
        false_record = records.browse([False])
        records = (
            real_record + new_record_origin + new_record_ref + new_record + false_record
        )
        with self.assertQueryCount(1):
            records.fetch(["name"])

    @warmup
    def test_search_fetch(self):
        records = self.env["test_performance.base"].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(2):
            self.env.invalidate_all()
            for record in records.search([]):
                record.partner_id

        with self.assertQueryCount(1):
            self.env.invalidate_all()
            for record in records.search_fetch([], ["partner_id"]):
                record.partner_id

        with self.assertQueryCount(2):
            self.env.invalidate_all()
            for record in records.search_fetch([], ["value_pc"]):
                record.partner_id

    @warmup
    def test_search_read(self):
        Model = self.env["test_performance.base"]
        records = Model.search([])
        self.assertEqual(len(records), 5)

        expected = records.read(["partner_id", "value_pc"])
        with self.assertQueryCount(2):
            self.env.invalidate_all()
            self.assertEqual(
                Model.search_read([], ["partner_id", "value_pc"]),
                expected,
            )

        expected = records.read(["partner_id", "value_pc"], load=False)
        with self.assertQueryCount(1):
            self.env.invalidate_all()
            self.assertEqual(
                Model.search_read([], ["partner_id", "value_pc"], load=False),
                expected,
            )

    @warmup
    def test_name_search(self):
        Model = self.env["test_performance.base"]
        record = Model.create({"name": "blablu"})
        record.invalidate_recordset()

        with self.assertQueryCount(1):
            Model.name_search("blablu")

    @users("__system__", "demo")
    @warmup
    def test_write_base(self):
        records = self.env["test_performance.base"].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(1):
            records.write({"name": "X"})

        with self.assertQueryCount(1):
            for index, record in enumerate(records):
                record.name = f"X {index}"

    @users("__system__", "demo")
    @warmup
    def test_write_base_with_recomputation(self):
        records = self.env["test_performance.base"].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(__system__=1, demo=1):
            records.write({"value": 42})

    @mute_logger("odoo.models.unlink")
    @users("__system__", "demo")
    @warmup
    def test_write_base_one2many(self):
        rec1 = self.env["test_performance.base"].create({"name": "X"})

        with self.assertQueryCount(3):
            self.env.invalidate_all()
            rec1.write({"line_ids": [Command.create({"value": 0})]})
        self.assertEqual(len(rec1.line_ids), 1)

        with self.assertQueryCount(4):
            self.env.invalidate_all()
            rec1.write(
                {"line_ids": [Command.create({"value": val}) for val in range(1, 12)]}
            )
        self.assertEqual(len(rec1.line_ids), 12)

        lines = rec1.line_ids

        with self.assertQueryCount(4):
            self.env.invalidate_all()
            rec1.write(
                {
                    "line_ids": [
                        Command.update(line.id, {"value": 42}) for line in lines[0]
                    ]
                }
            )
        self.assertEqual(rec1.line_ids, lines)

        with self.assertQueryCount(4):
            self.env.invalidate_all()
            rec1.write(
                {
                    "line_ids": [
                        Command.update(line.id, {"value": 42 + line.id})
                        for line in lines[1:]
                    ]
                }
            )
        self.assertEqual(rec1.line_ids, lines)

        with self.assertQueryCount(10):
            self.env.invalidate_all()
            rec1.write({"line_ids": [Command.delete(line.id) for line in lines[0]]})
        self.assertEqual(rec1.line_ids, lines[1:])

        with self.assertQueryCount(9):
            self.env.invalidate_all()
            rec1.write({"line_ids": [Command.delete(line.id) for line in lines[1:]]})
        self.assertFalse(rec1.line_ids)
        self.assertFalse(lines.exists())

        rec1.write({"line_ids": [Command.create({"value": val}) for val in range(12)]})
        lines = rec1.line_ids

        with self.assertQueryCount(9):
            self.env.invalidate_all()
            rec1.write({"line_ids": [Command.unlink(line.id) for line in lines[0]]})
        self.assertEqual(rec1.line_ids, lines[1:])

        with self.assertQueryCount(9):
            self.env.invalidate_all()
            rec1.write({"line_ids": [Command.unlink(line.id) for line in lines[1:]]})
        self.assertFalse(rec1.line_ids)
        self.assertFalse(lines.exists())

        rec1.write({"line_ids": [Command.create({"value": val}) for val in range(12)]})
        lines = rec1.line_ids
        rec2 = self.env["test_performance.base"].create({"name": "X"})

        with self.assertQueryCount(6):
            self.env.invalidate_all()
            rec2.write({"line_ids": [Command.link(line.id) for line in lines[0]]})
        self.assertEqual(rec1.line_ids, lines[1:])
        self.assertEqual(rec2.line_ids, lines[0])

        with self.assertQueryCount(6):
            self.env.invalidate_all()
            rec2.write({"line_ids": [Command.link(line.id) for line in lines[1:]]})
        self.assertFalse(rec1.line_ids)
        self.assertEqual(rec2.line_ids, lines)

        with self.assertQueryCount(3):
            self.env.invalidate_all()
            rec2.write({"line_ids": [Command.link(line.id) for line in lines[0]]})
        self.assertEqual(rec2.line_ids, lines)

        with self.assertQueryCount(3):
            self.env.invalidate_all()
            rec2.write({"line_ids": [Command.link(line.id) for line in lines[1:]]})
        self.assertEqual(rec2.line_ids, lines)

        with self.assertQueryCount(10):
            self.env.invalidate_all()
            rec2.write({"line_ids": [Command.clear()]})
        self.assertFalse(rec2.line_ids)

        with self.assertQueryCount(3):
            self.env.invalidate_all()
            rec2.write({"line_ids": [Command.clear()]})
        self.assertFalse(rec2.line_ids)

        rec1.write({"line_ids": [Command.create({"value": val}) for val in range(12)]})
        lines = rec1.line_ids

        with self.assertQueryCount(6):
            self.env.invalidate_all()
            rec2.write({"line_ids": [Command.set(lines[0].ids)]})
        self.assertEqual(rec1.line_ids, lines[1:])
        self.assertEqual(rec2.line_ids, lines[0])

        with self.assertQueryCount(5):
            self.env.invalidate_all()
            rec2.write({"line_ids": [Command.set(lines.ids)]})
        self.assertFalse(rec1.line_ids)
        self.assertEqual(rec2.line_ids, lines)

        with self.assertQueryCount(4):
            self.env.invalidate_all()
            rec2.write({"line_ids": [Command.set(lines.ids)]})
        self.assertEqual(rec2.line_ids, lines)

    @mute_logger("odoo.models.unlink")
    def test_write_base_one2many_with_constraint(self):
        rec = self.env["test_performance.base"].create({"name": "Y"})
        rec.write({"line_ids": [Command.create({"value": val}) for val in range(12)]})

        rec.write(
            {
                "line_ids": [Command.clear()]
                + [Command.create({"value": val}) for val in range(6)]
            }
        )
        self.assertEqual(len(rec.line_ids), 6)

    @mute_logger("odoo.models.unlink")
    @users("__system__", "demo")
    @warmup
    def test_write_base_many2many(self):
        rec1 = self.env["test_performance.base"].create({"name": "X"})

        with self.assertQueryCount(4):
            self.env.invalidate_all()
            rec1.write({"tag_ids": [Command.create({"name": 0})]})
        self.assertEqual(len(rec1.tag_ids), 1)

        with self.assertQueryCount(4):
            self.env.invalidate_all()
            rec1.write(
                {"tag_ids": [Command.create({"name": val}) for val in range(1, 12)]}
            )
        self.assertEqual(len(rec1.tag_ids), 12)

        tags = rec1.tag_ids

        with self.assertQueryCount(3):
            self.env.invalidate_all()
            rec1.write(
                {"tag_ids": [Command.update(tag.id, {"name": "X"}) for tag in tags[0]]}
            )
        self.assertEqual(rec1.tag_ids, tags)

        with self.assertQueryCount(3):
            self.env.invalidate_all()
            rec1.write(
                {"tag_ids": [Command.update(tag.id, {"name": "X"}) for tag in tags[1:]]}
            )
        self.assertEqual(rec1.tag_ids, tags)

        with self.assertQueryCount(__system__=6, demo=6):
            self.env.invalidate_all()
            rec1.write({"tag_ids": [Command.delete(tag.id) for tag in tags[0]]})
        self.assertEqual(rec1.tag_ids, tags[1:])

        with self.assertQueryCount(__system__=6, demo=6):
            self.env.invalidate_all()
            rec1.write({"tag_ids": [Command.delete(tag.id) for tag in tags[1:]]})
        self.assertFalse(rec1.tag_ids)
        self.assertFalse(tags.exists())

        rec1.write({"tag_ids": [Command.create({"name": val}) for val in range(12)]})
        tags = rec1.tag_ids

        with self.assertQueryCount(3):
            self.env.invalidate_all()
            rec1.write({"tag_ids": [Command.unlink(tag.id) for tag in tags[0]]})
        self.assertEqual(rec1.tag_ids, tags[1:])

        with self.assertQueryCount(3):
            self.env.invalidate_all()
            rec1.write({"tag_ids": [Command.unlink(tag.id) for tag in tags[1:]]})
        self.assertFalse(rec1.tag_ids)
        self.assertTrue(tags.exists())

        rec2 = self.env["test_performance.base"].create({"name": "X"})

        with self.assertQueryCount(3):
            self.env.invalidate_all()
            rec2.write({"tag_ids": [Command.link(tag.id) for tag in tags[0]]})
        self.assertEqual(rec2.tag_ids, tags[0])

        with self.assertQueryCount(3):
            self.env.invalidate_all()
            rec2.write({"tag_ids": [Command.link(tag.id) for tag in tags[1:]]})
        self.assertEqual(rec2.tag_ids, tags)

        with self.assertQueryCount(2):
            self.env.invalidate_all()
            rec2.write({"tag_ids": [Command.link(tag.id) for tag in tags[1:]]})
        self.assertEqual(rec2.tag_ids, tags)

        with self.assertQueryCount(3):
            self.env.invalidate_all()
            rec2.write({"tag_ids": [Command.clear()]})
        self.assertFalse(rec2.tag_ids)
        self.assertTrue(tags.exists())

        with self.assertQueryCount(2):
            self.env.invalidate_all()
            rec2.write({"tag_ids": [Command.clear()]})
        self.assertFalse(rec2.tag_ids)

        with self.assertQueryCount(3):
            self.env.invalidate_all()
            rec2.write({"tag_ids": [Command.set(tags.ids)]})
        self.assertEqual(rec2.tag_ids, tags)

        with self.assertQueryCount(3):
            self.env.invalidate_all()
            rec2.write({"tag_ids": [Command.set(tags[:8].ids)]})
        self.assertEqual(rec2.tag_ids, tags[:8])

        with self.assertQueryCount(4):
            self.env.invalidate_all()
            rec2.write({"tag_ids": [Command.set(tags[4:].ids)]})
        self.assertEqual(rec2.tag_ids, tags[4:])

        with self.assertQueryCount(3):
            self.env.invalidate_all()
            rec2.write({"tag_ids": [Command.set(tags.ids)]})
        self.assertEqual(rec2.tag_ids, tags)

        with self.assertQueryCount(2):
            self.env.invalidate_all()
            rec2.write({"tag_ids": [Command.set(tags.ids)]})
        self.assertEqual(rec2.tag_ids, tags)

    @users("__system__", "demo")
    @warmup
    def test_create_base(self):
        with self.assertQueryCount(__system__=2, demo=2):
            self.env["test_performance.base"].create({"name": "X"})

    @users("__system__", "demo")
    @warmup
    def test_create_base_with_lines(self):
        with self.assertQueryCount(3):
            self.env["test_performance.base"].create(
                {
                    "name": "X",
                    "line_ids": [Command.create({"value": val}) for val in range(10)],
                }
            )

    @users("__system__", "demo")
    def test_create_base_with_lines_does_not_grow_with_the_lines(self):
        self.assertQueriesConstant(
            lambda lines: self.env["test_performance.base"].create(
                {
                    "name": "X",
                    "line_ids": [
                        Command.create({"value": val}) for val in range(lines)
                    ],
                }
            ),
            small=2,
            large=40,
        )

    @users("__system__", "demo")
    def test_create_many_bases_does_not_grow_with_the_batch(self):
        self.assertQueriesConstant(
            lambda size: self.env["test_performance.base"].create(
                [{"name": f"X{i}", "value": i} for i in range(size)]
            ),
            small=2,
            large=40,
        )

    @users("__system__", "demo")
    @warmup
    def test_create_base_with_tags(self):
        with self.assertQueryCount(2):
            self.env["test_performance.base"].create({"name": "X"})

        with self.assertQueryCount(4):
            self.env["test_performance.base"].create(
                {
                    "name": "X",
                    "tag_ids": [Command.create({"name": val}) for val in range(10)],
                }
            )

        tags = self.env["test_performance.tag"].create(
            [{"name": val} for val in range(10)]
        )

        with self.assertQueryCount(3):
            self.env["test_performance.base"].create(
                {
                    "name": "X",
                    "tag_ids": [Command.link(tag.id) for tag in tags],
                }
            )

        with self.assertQueryCount(2):
            self.env["test_performance.base"].create(
                {
                    "name": "X",
                    "tag_ids": [Command.set([])],
                }
            )

        with self.assertQueryCount(3):
            self.env["test_performance.base"].create(
                {
                    "name": "X",
                    "tag_ids": [Command.set(tags.ids)],
                }
            )

    @users("__system__", "demo")
    @warmup
    def test_several_prefetch(self):
        initial_records = self.env["test_performance.base"].search([])
        self.assertEqual(len(initial_records), 5)
        for _i in range(8):
            self.env.cr.execute(
                "insert into test_performance_base(value) select value from test_performance_base"
            )
        records = self.env["test_performance.base"].search([])
        self.assertEqual(len(records), 1280)

        with self.assertQueryCount(__system__=1, demo=1):
            records.mapped("value")

        with self.assertQueryCount(__system__=1, demo=1):
            records.invalidate_model(["value"])
            records.mapped("value")

        with self.assertQueryCount(__system__=1, demo=1):
            records.invalidate_model(["value"])
            new_recs = records.browse(
                records.new(origin=record).id for record in records
            )
            new_recs.mapped("value")

        self.env.cr.execute(
            "delete from test_performance_base where id != ALL(%s)",
            (list(initial_records.ids),),
        )

    def test_prefetch_compute(self):
        records = self.env["test_performance.base"].create(
            [{"name": str(i), "value": i} for i in [1, 2, 3]]
        )
        self.env.flush_all()
        self.env.invalidate_all()

        with self.assertQueries([], flush=False):
            records[1].value = 42

        queries = [
            """ SELECT "test_performance_base"."id",
                       "test_performance_base"."name",
                       "test_performance_base"."value",
                       "test_performance_base"."value_pc",
                       "test_performance_base"."partner_id",
                       "test_performance_base"."total",
                       "test_performance_base"."create_uid",
                       "test_performance_base"."create_date",
                       "test_performance_base"."write_uid",
                       "test_performance_base"."write_date"
                FROM "test_performance_base"
                WHERE "test_performance_base"."id" IN (%s)
            """,
        ]
        with self.assertQueries(queries, flush=False):
            result_name = [record.name for record in records]

        with self.assertQueries([], flush=False):
            result_value = [record.value for record in records]

        with self.assertQueries([], flush=False):
            result_value_pc = [record.value_pc for record in records]

        result = list(zip(result_name, result_value, result_value_pc, strict=False))
        self.assertEqual(result, [("1", 1, 0.01), ("2", 42, 0.42), ("3", 3, 0.03)])

    def test_prefetch_new(self):
        model = self.env["test_performance.base"]
        records = model.create(
            [
                {"name": str(i), "line_ids": [Command.create({"value": i})]}
                for i in [1, 2, 3]
            ]
        )
        self.env.flush_all()
        self.env.invalidate_all()

        new_record = model.new({"line_ids": [Command.create({"value": 4})]})
        new_records_ids = [model.new(origin=record).id for record in records]
        new_records_ids.append(new_record.id)
        new_records = model.browse(new_records_ids)

        with self.assertQueryCount(2):
            for record in new_records:
                for line in record.line_ids:
                    line.value


@tagged("bacon_and_eggs")
class TestIrPropertyOptimizations(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Bacon = self.env["test_performance.bacon"]
        self.Eggs = self.env["test_performance.eggs"]

    def test_with_falsy_default(self):
        self.assertFalse(
            self.env["ir.default"]._get(
                "test_performance.bacon", "property_eggs", company_id=True
            )
        )

        eggs = self.Eggs.create({})
        self.Bacon.create({})
        self.Bacon.create({"property_eggs": eggs.id})

        with self.assertQueryCount(1):
            self.Bacon.create({})

        with self.assertQueryCount(1):
            self.Bacon.with_context(default_property_eggs=False).create({})

        with self.assertQueryCount(1):
            self.Bacon.create({"property_eggs": False})

        with self.assertQueryCount(1):
            self.Bacon.with_context(default_property_eggs=eggs.id).create({})

        with self.assertQueryCount(1):
            self.Bacon.create({"property_eggs": eggs.id})

    def test_with_truthy_default(self):
        eggs = self.Eggs.create({})
        self.env["ir.default"].set("test_performance.bacon", "property_eggs", eggs.id)

        self.assertEqual(
            eggs.id,
            self.env["ir.default"]._get("test_performance.bacon", "property_eggs"),
        )

        self.Bacon.create({})

        with self.assertQueryCount(1):
            self.Bacon.create({})

        with self.assertQueryCount(1):
            self.Bacon.with_context(default_property_eggs=eggs.id).create({})

        with self.assertQueryCount(1):
            self.Bacon.create({"property_eggs": eggs.id})

        eggs = self.Eggs.create({})
        self.Bacon.create({"property_eggs": eggs.id})

        with self.assertQueryCount(1):
            self.Bacon.with_context(default_property_eggs=eggs.id).create({})

        with self.assertQueryCount(1):
            self.Bacon.create({"property_eggs": eggs.id})

        with self.assertQueryCount(1):
            self.Bacon.with_context(default_property_eggs=False).create({})

        with self.assertQueryCount(1):
            self.Bacon.create({"property_eggs": False})


@tagged("mapped_perf")
class TestMapped(TransactionCase):
    def test_relational_mapped(self):
        recs = self.env["test_performance.base"].create(
            [
                {
                    "name": "foo%d" % index,
                    "line_ids": [Command.create({"value": index})],
                }
                for index in range(1000)
            ]
        )
        self.env.flush_all()
        self.env.invalidate_all()

        with self.assertQueryCount(2):
            for rec in recs:
                rec.line_ids.mapped("value")


@tagged("increment_perf")
class TestIncrementFieldsSkipLock(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.record = cls.env["test_performance.mozzarella"].create(
            [
                {
                    "value": 1,
                    "value_plus_one": 2,
                }
            ]
        )
        cls.other_record = cls.env["test_performance.mozzarella"].create(
            [
                {
                    "value": 10,
                    "value_plus_one": 11,
                }
            ]
        )

    def test_increment_fields_skiplock_one_field(self):
        with self.assertQueryCount(1):
            did_update = self.record._increment_fields_skiplock("value")
            _logger.info(
                "increment_fields_skiplock did %supdate the field",
                "" if did_update else "not ",
            )

        self.assertTrue(
            did_update,
            "increment_fields_skiplock should have updated the field: "
            "no concurrent transaction holds the row lock.",
        )
        # the increment dropped the counter from the cache: the read that
        # follows fetches the row, without an invalidation by the caller
        with self.assertQueryCount(1):
            self.assertEqual(
                self.record.value,
                2,
                "increment_fields_skiplock should have incremented this field.",
            )
            self.assertEqual(
                self.record.value_plus_one,
                2,
                "This value should not have been incremented, irrespective of the presence of a lock or not.",
            )

        self.assertEqual(
            self.other_record.value,
            10,
            "other_record should not have been updated.",
        )
        self.assertEqual(
            self.other_record.value_plus_one,
            11,
            "other_record should not have been updated.",
        )

    def test_increment_fields_skiplock_multiple_fields(self):
        with self.assertQueryCount(1):
            did_update = self.record._increment_fields_skiplock(
                "value", "value_plus_one"
            )
            _logger.info(
                "increment_fields_skiplock did %supdate the fields",
                "" if did_update else "not ",
            )

        self.record.invalidate_recordset()

        self.assertTrue(
            did_update,
            "increment_fields_skiplock should have updated the fields: "
            "no concurrent transaction holds the row lock.",
        )
        with self.assertQueryCount(1):
            self.assertEqual(
                self.record.value,
                2,
                "increment_fields_skiplock should have incremented this field.",
            )
            self.assertEqual(
                self.record.value_plus_one,
                3,
                "increment_fields_skiplock should have incremented this field.",
            )

        self.assertEqual(
            self.other_record.value,
            10,
            "other_record should not have been updated.",
        )
        self.assertEqual(
            self.other_record.value_plus_one,
            11,
            "other_record should not have been updated.",
        )

    def test_increment_fields_skiplock_null_field(self):
        self.env.cr.execute(
            "SELECT value_null_by_default FROM test_performance_mozzarella WHERE id = %s",
            (self.record.id,),
        )
        [value] = self.env.cr.fetchone()
        self.assertIsNone(value)
        self.assertEqual(self.record.value_null_by_default, 0)
        with self.assertQueryCount(1):
            self.record._increment_fields_skiplock("value_null_by_default")
        self.record.invalidate_recordset(["value_null_by_default"])
        self.assertEqual(self.record.value_null_by_default, 1)


@tagged("post_install", "-at_install")
class TestAssertQueriesConstant(TransactionCase):
    def test_a_batch_of_reads_served_by_one_fetch_passes(self):
        def read_batch(size):
            records = self.env["test_performance.base"].create(
                [{"name": f"X{i}"} for i in range(size)]
            )
            self.env.invalidate_all()
            records.mapped("name")

        self.assertQueriesConstant(read_batch, small=2, large=20)

    def test_a_read_per_record_fails(self):
        def n_plus_one(size):
            records = self.env["test_performance.base"].create(
                [{"name": f"X{i}"} for i in range(size)]
            )
            for record in records:
                self.env.invalidate_all()
                _ = record.name

        with self.assertRaisesRegex(AssertionError, "grows with the batch"):
            self.assertQueriesConstant(n_plus_one, small=2, large=20)
