import base64
import io
import threading
from collections import OrderedDict
from datetime import date, datetime
from unittest.mock import patch

import psycopg2
from PIL import Image

from odoo import Command, fields, models
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.fields import Domain
from odoo.tests import TransactionCase, tagged, users
from odoo.tools import float_repr, mute_logger
from odoo.tools.image import image_data_uri

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.addons.base.tests.files import SVG_B64, ZIP_RAW
from odoo.addons.base.tests.test_expression import TransactionExpressionCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestFieldParametersValidation(TransactionCase):
    def test_invalid_parameter(self):
        from odoo.orm.model_classes import add_to_registry  # noqa: PLC0415

        class Foo(models.Model):
            _module = None
            _name = _description = 'test_orm.field_parameter_validation'

            name = fields.Char(invalid_parameter=42)

        add_to_registry(self.registry, Foo)
        self.addCleanup(self.registry.__delitem__, Foo._name)

        with self.assertLogs('odoo.fields', level='WARNING') as cm:
            self.registry._setup_models__(self.env.cr, [])  # incremental setup

        self.assertTrue(cm.output[0].startswith(
            "WARNING:odoo.fields:Field test_orm.field_parameter_validation.name: "
            "unknown parameter 'invalid_parameter'",
        ))


def select(model, *fnames):
    """ Return the expected query string to SELECT the given columns. """
    table = model._table
    model_fields = model._fields
    terms = ", ".join(
        f'"{table}"."{fname}"' if not model_fields[fname].translate else f'"{table}"."{fname}"->>%s'
        for fname in ['id'] + list(fnames)
    )
    return f'SELECT {terms} FROM "{table}" WHERE "{table}"."id" IN %s'


def insert(model, *fnames, rowcount=1):
    """ Return the expected query string to INSERT the given columns. """
    columns = sorted(fnames + ('create_uid', 'create_date', 'write_uid', 'write_date'))
    header = ", ".join(f'"{column}"' for column in columns)
    template = ", ".join("%s" for _index in range(rowcount))
    return f'INSERT INTO "{model._table}" ({header}) VALUES {template} RETURNING "id"'


def update(model, *fnames):
    """ Return the expected query string to UPDATE the given columns. """
    table = f'"{model._table}"'
    fnames = sorted(fnames + ('write_uid', 'write_date'))
    columns = ", ".join(f'"{column}"' for column in fnames)
    assignments = ", ".join(
        f'"{fname}" = "__tmp"."{fname}"::{model._fields[fname].column_type[1]}'
        for fname in fnames
    )
    return (
        f'UPDATE {table} SET {assignments} '
        f'FROM (VALUES %s) AS "__tmp"("id", {columns}) '
        f'WHERE {table}."id" = "__tmp"."id"'
    )


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestComputeQueries(TransactionCase):
    """ Test the queries made by create() with computed fields. """

    def test_compute_readonly(self):
        model = self.env['test_orm.compute.readonly']
        model.create({})

        # no value, no default
        with self.assertQueries([insert(model, 'foo'), update(model, 'bar')]):
            record = model.create({'foo': 'Foo'})
        self.assertEqual(record.bar, 'Foo')

        # some value, no default
        with self.assertQueries([insert(model, 'foo', 'bar'), update(model, 'bar')]):
            record = model.create({'foo': 'Foo', 'bar': 'Bar'})
        self.assertEqual(record.bar, 'Foo')

        model = model.with_context(default_bar='Def')

        # no value, some default
        with self.assertQueries([insert(model, 'foo', 'bar'), update(model, 'bar')]):
            record = model.create({'foo': 'Foo'})
        self.assertEqual(record.bar, 'Foo')

        # some value, some default
        with self.assertQueries([insert(model, 'foo', 'bar'), update(model, 'bar')]):
            record = model.create({'foo': 'Foo', 'bar': 'Bar'})
        self.assertEqual(record.bar, 'Foo')

    def test_compute_readwrite(self):
        model = self.env['test_orm.compute.readwrite']
        model.create({})

        # no value, no default
        with self.assertQueries([insert(model, 'foo'), update(model, 'bar')]):
            record = model.create({'foo': 'Foo'})
        self.assertEqual(record.bar, 'Foo')

        # some value, no default
        with self.assertQueries([insert(model, 'foo', 'bar')]):
            record = model.create({'foo': 'Foo', 'bar': 'Bar'})
        self.assertEqual(record.bar, 'Bar')

        model = model.with_context(default_bar='Def')

        # no value, some default
        with self.assertQueries([insert(model, 'foo', 'bar')]):
            record = model.create({'foo': 'Foo'})
        self.assertEqual(record.bar, 'Def')

        # some value, some default
        with self.assertQueries([insert(model, 'foo', 'bar')]):
            record = model.create({'foo': 'Foo', 'bar': 'Bar'})
        self.assertEqual(record.bar, 'Bar')

    def test_compute_inverse(self):
        model = self.env['test_orm.compute.inverse']
        model.create({})

        # no value, no default
        with self.assertQueries([insert(model, 'foo'), update(model, 'bar')]):
            record = model.create({'foo': 'Foo'})
        self.assertEqual(record.foo, 'Foo')
        self.assertEqual(record.bar, 'Foo')

        # some value, no default
        with self.assertQueries([insert(model, 'foo', 'bar'), update(model, 'foo')]):
            record = model.create({'foo': 'Foo', 'bar': 'Bar'})
        self.assertEqual(record.foo, 'Bar')
        self.assertEqual(record.bar, 'Bar')

        model = model.with_context(default_bar='Def')

        # no value, some default
        with self.assertQueries([insert(model, 'foo', 'bar'), update(model, 'foo')]):
            record = model.create({'foo': 'Foo'})
        self.assertEqual(record.foo, 'Def')
        self.assertEqual(record.bar, 'Def')

        # some value, some default
        with self.assertQueries([insert(model, 'foo', 'bar'), update(model, 'foo')]):
            record = model.create({'foo': 'Foo', 'bar': 'Bar'})
        self.assertEqual(record.foo, 'Bar')
        self.assertEqual(record.bar, 'Bar')

    def test_x2many_computed_inverse(self):
        record = self.env['test_orm.compute.inverse'].create(
            {'child_ids': [Command.create({'foo': 'child'})]},
        )
        self.assertEqual(
            len(record.child_ids), 1,
            f"Should be a single record: {record.child_ids!r}",
        )
        self.assertTrue(
            record.child_ids.id,
            f"Should be database records: {record.child_ids!r}",
        )
        self.assertEqual(record.foo, 'has one child')

    def test_multi_create(self):
        model = self.env['test_orm.foo']
        model.create({})

        with self.assertQueries([insert(model, 'name', 'value1', 'value2', rowcount=4)]):
            create_values = [
                {'name': 'Foo1', 'value1': 10},
                {'name': 'Foo2', 'value2': 12},
                {'name': 'Foo3'},
                {},
            ]
            records = model.create(create_values)
        self.assertEqual(records.mapped('name'), ['Foo1', 'Foo2', 'Foo3', False])
        self.assertEqual(records.mapped('value1'), [10, 0, 0, 0])
        self.assertEqual(records.mapped('value2'), [0, 12, 0, 0])

    def test_create_cache_consistency(self):
        """ The cache should always contains the raw value of the database. The
        cache value of non-assigned column during create() should be None for
        any column field type.
        """
        record = self.env['test_orm.create.performance'].create({})
        self.assertEqual(record.confirmed, False)
        cached_value = record._cache['confirmed']

        # the cached value should be the same as if we had fetched it from database
        record.invalidate_recordset()
        record.fetch(['confirmed'])
        self.assertEqual(record._cache['confirmed'], cached_value)

    def test_create_cache_of_compute_store_fields(self):
        model = self.env['test_orm.create.performance']
        model.create({})  # warmup

        with self.assertQueryCount(2):  # one for create + one to update name_changes
            record = model.create({'name': 'blabla'})
            self.assertEqual(record.name_changes, 1)

    def test_create_x2many_performance(self):
        model = self.env['test_orm.create.performance']
        model.create({})  # warmup

        # 1 INSERT on model table (without the pending update of name_changes)
        with self.assertQueryCount(1, flush=False):
            record = model.create({})
        with self.assertQueryCount(0):
            self.assertFalse(record.line_ids)
        with self.assertQueryCount(0):
            self.assertFalse(record.tag_ids)

        # 1 INSERT on model table (without the pending update of name_changes)
        with self.assertQueryCount(1, flush=False):
            record = model.create({
                'line_ids': [],
                'tag_ids': [],
            })
        with self.assertQueryCount(0):
            self.assertFalse(record.line_ids)
        with self.assertQueryCount(0):
            self.assertFalse(record.tag_ids)

        # warmup for defaults in secondary models
        record = model.create({
            'line_ids': [Command.create({})],
            'tag_ids': [Command.create({})],
        })

        # 1 INSERT on model table (without the pending update of name_changes)
        # 1 INSERT on table of comodel of line_ids
        # 1 INSERT on table of comodel of tag_ids
        # 1 INSERT on relation of tag_ids
        with self.assertQueryCount(4, flush=False):
            record = model.create({
                'line_ids': [Command.create({})],
                'tag_ids': [Command.create({})],
            })
        with self.assertQueryCount(0):
            self.assertTrue(record.line_ids)
        with self.assertQueryCount(0):
            self.assertTrue(record.tag_ids)

    def test_partial_compute_batching(self):
        """ Create several 'new' records and check that the partial compute
        method is called only once.
        """
        order = self.env['test_orm.order'].new({
            'line_ids': [Command.create({'reward': False})] * 100,
        })

        OrderLine = self.env.registry['test_orm.order.line']
        with patch.object(
            OrderLine,
            '_compute_has_been_rewarded',
            side_effect=OrderLine._compute_has_been_rewarded,
            autospec=True,
        ) as patch_compute:
            order.line_ids.mapped('has_been_rewarded')
            self.assertEqual(patch_compute.call_count, 1)


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestComputeSudo(TransactionCaseWithUserDemo):
    def test_compute_sudo_depends_context_uid(self):
        record = self.env['test_orm.compute.sudo'].create({})
        self.assertEqual(record.with_user(self.user_demo).name_for_uid, self.user_demo.name)


@tagged('unlink_constraints')
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestUnlinkConstraints(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        MODEL = cls.env['test_orm.model_constrained_unlinks']
        cls.deletable_foo = MODEL.create({'foo': 'formaggio'})
        cls.undeletable_foo = MODEL.create({'foo': 'prosciutto'})
        cls.deletable_bar = MODEL.create({'bar': 5})
        cls.undeletable_bar = MODEL.create({'bar': 6})

    def test_unlink_manual(self):
        self.assertTrue(self.deletable_foo.unlink())
        self.assertTrue(self.deletable_bar.unlink())

        # should both fail because of ondelete method
        with self.assertRaises(ValueError, msg="You didn't say if you wanted it crudo or cotto..."):
            self.undeletable_foo.unlink()
        with self.assertRaises(ValueError, msg="Nooooooooo bar can't be greater than five!!"):
            self.undeletable_bar.unlink()

    def test_unlink_uninstall(self):
        self.patch(self.registry, 'uninstalling_modules', {'test_orm'})

        self.assertTrue(self.deletable_foo.unlink())
        self.assertTrue(self.deletable_bar.unlink())

        # should fail since it's at_uninstall=True
        with self.assertRaises(ValueError, msg="You didn't say if you wanted it crudo or cotto..."):
            self.undeletable_foo.unlink()

        # should succeed since it's at_uninstall=False
        self.assertTrue(self.undeletable_bar.unlink())


@tagged('wrong_related_path')
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestWrongRelatedError(TransactionCase):
    def test_wrong_related_path(self):
        from odoo.orm.model_classes import add_to_registry  # noqa: PLC0415

        class Foo(models.Model):
            _module = None
            _name = _description = 'test_orm.wrong_related_path'

            foo_id = fields.Many2one('test_orm.foo')
            foo_non_existing = fields.Char(related='foo_id.non_existing_field')
        add_to_registry(self.registry, Foo)
        self.addCleanup(self.registry.__delitem__, Foo._name)

        errMsg = (
            "Field non_existing_field referenced in related field definition "
            "test_orm.wrong_related_path.foo_non_existing does not exist."
        )
        with self.assertRaisesRegex(KeyError, errMsg):
            self.registry._setup_models__(self.env.cr, [])  # incremental setup


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestPrecomputeModel(TransactionCase):

    def test_precompute_consistency(self):
        Model = self.registry['test_orm.precompute']
        self.assertEqual(Model.lower.compute, Model.upper.compute)
        self.assertTrue(Model.lower.precompute)
        self.assertTrue(Model.upper.precompute)

        # see what happens if not both are precompute
        self.addCleanup(self.registry.reset_changes)
        self.patch(Model.upper, 'precompute', False)
        with self.assertWarns(UserWarning):
            self.registry._setup_models__(self.cr, ['test_orm.precompute'])
            self.registry.field_computed

    def test_precompute_dependencies_base(self):
        Model = self.registry['test_orm.precompute']
        self.assertTrue(Model.lower.precompute)
        self.assertTrue(Model.upper.precompute)
        self.assertTrue(Model.lowup.precompute)

        # see what happens if precompute depends on non-precompute
        self.addCleanup(self.registry.reset_changes)

        def reset():
            Model.lowup.precompute = True
        self.addCleanup(reset)
        self.patch(Model.lower, 'precompute', False)
        self.patch(Model.upper, 'precompute', False)

        with self.assertWarns(UserWarning):
            self.registry._setup_models__(self.cr, ['test_orm.precompute'])
            self.registry.get_trigger_tree(Model._fields.values())

    def test_precompute_dependencies_many2one(self):
        Model = self.registry['test_orm.precompute']
        Partner = self.registry['res.partner']

        # Model.commercial_id depends on partner_id.commercial_partner_id, and
        # precomputation is valid when traversing many2one fields
        self.assertTrue(Model.commercial_id.precompute)
        self.assertFalse(Partner.commercial_partner_id.precompute)

    def test_precompute_dependencies_one2many(self):
        Model = self.registry['test_orm.precompute']
        Line = self.registry['test_orm.precompute.line']
        self.assertTrue(Model.size.precompute)
        self.assertTrue(Line.size.precompute)

        # see what happens if precompute depends on non-precompute
        self.addCleanup(self.registry.reset_changes)
        # ensure that Model.size.precompute is restored after _setup_models__()
        self.patch(Model.size, 'precompute', True)
        self.patch(Line.size, 'precompute', False)
        with self.assertWarns(UserWarning):
            self.registry._setup_models__(self.cr, ['test_orm.precompute', 'test_orm.precompute.line'])
            self.registry.get_trigger_tree(Model._fields.values())


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestPrecompute(TransactionCase):

    def test_precompute(self):

        model = self.env['test_orm.precompute']
        Model = self.registry['test_orm.precompute']
        self.assertTrue(Model.lower.precompute)
        self.assertTrue(Model.upper.precompute)
        self.assertTrue(Model.lowup.precompute)

        # warmup
        model.create({'name': 'Foo', 'line_ids': [Command.create({'name': 'bar'})]})
        # the creation makes one insert query for the main record, and one for the line
        with self.assertQueries([
            insert(model, 'name', 'lower', 'upper', 'lowup', 'commercial_id', 'size'),
            insert(model.line_ids, 'parent_id', 'name', 'size'),
        ]):
            record = model.create({'name': 'Foo', 'line_ids': [Command.create({'name': 'bar'})]})

        # check the values in the database
        self.cr.execute(f'SELECT * FROM "{model._table}" WHERE id=%s', [record.id])
        [row] = self.cr.dictfetchall()

        self.assertEqual(row['name'], 'Foo')
        self.assertEqual(row['lower'], 'foo')
        self.assertEqual(row['upper'], 'FOO')
        self.assertEqual(row['lowup'], 'fooFOO')
        self.assertEqual(row['size'], 3)

    def test_precompute_combo(self):
        model = self.env['test_orm.precompute.combo']

        # warmup
        model.create({})
        QUERIES = [insert(model, 'name', 'reader', 'editer', 'setter')]

        # no value at all
        with self.assertQueries(QUERIES):
            record = model.create({'name': 'A'})

        self.assertEqual(record.reader, 'A')
        self.assertEqual(record.editer, 'A')
        self.assertEqual(record.setter, 'A')

        # default value
        with self.assertQueries(QUERIES), self.assertLogs('precompute_setter', level='WARNING'):
            defaults = dict(default_reader='X', default_editer='Y', default_setter='Z')
            record = model.with_context(**defaults).create({'name': 'A'})

        self.assertEqual(record.reader, 'A')
        self.assertEqual(record.editer, 'Y')
        self.assertEqual(record.setter, 'Z')

        # explicit value
        with self.assertQueries(QUERIES), self.assertLogs('precompute_setter', level='WARNING'):
            record = model.create({'name': 'A', 'reader': 'X', 'editer': 'Y', 'setter': 'Z'})

        self.assertEqual(record.reader, 'A')
        self.assertEqual(record.editer, 'Y')
        self.assertEqual(record.setter, 'Z')

    def test_precompute_editable(self):
        model = self.env['test_orm.precompute.editable']

        # no value for bar, no value for baz
        record = model.create({'foo': 'foo'})
        self.assertEqual(record.bar, 'COMPUTED')
        self.assertEqual(record.baz, 'COMPUTED')
        self.assertEqual(record.baz2, 'COMPUTED')

        # value for bar, no value for baz
        record = model.create({'foo': 'foo', 'bar': 'bar'})
        self.assertEqual(record.bar, 'bar')
        self.assertEqual(record.baz, 'COMPUTED')
        self.assertEqual(record.baz2, 'COMPUTED')

        # no value for bar, value for baz: the computation of bar should not
        # recompute baz in memory, in case a third field depends on it
        record = model.create({'foo': 'foo', 'baz': 'baz'})
        self.assertEqual(record.bar, 'COMPUTED')
        self.assertEqual(record.baz, 'baz')
        self.assertEqual(record.baz2, 'baz')

        # value for bar, value for baz
        record = model.create({'foo': 'foo', 'bar': 'bar', 'baz': 'baz'})
        self.assertEqual(record.bar, 'bar')
        self.assertEqual(record.baz, 'baz')
        self.assertEqual(record.baz2, 'baz')

    def test_precompute_readonly(self):
        """
        Ensures
        - a stored, precomputed, readonly field cannot be altered by the user,
        - a stored, precomputed, readonly field,
          but with a states attributes changing the readonly of the field according to the state of the record,
          can be altered by the user.
        The `bar` field is store=True, precompute=True, readonly=True
        The `baz` field is store=True, precompute=True, readonly=False,
        """
        model = self.env['test_orm.precompute.readonly']

        # no value for bar, no value for baz
        record = model.create({'foo': 'foo'})
        self.assertEqual(record.bar, 'COMPUTED')
        self.assertEqual(record.baz, 'COMPUTED')

        # value for bar, no value for baz
        # bar is readonly, it must ignore the value for bar in the create values
        record = model.create({'foo': 'foo', 'bar': 'bar'})
        self.assertEqual(record.bar, 'COMPUTED')
        self.assertEqual(record.baz, 'COMPUTED')

        # no value for bar, value for baz
        # baz is readonly=False
        # the value for baz must be taken into account
        record = model.create({'foo': 'foo', 'baz': 'baz'})
        self.assertEqual(record.bar, 'COMPUTED')
        self.assertEqual(record.baz, 'baz')

        # value for bar, value for baz
        # bar must be ignored
        # baz must be taken into account
        record = model.create({'foo': 'foo', 'bar': 'bar', 'baz': 'baz'})
        self.assertEqual(record.bar, 'COMPUTED')
        self.assertEqual(record.baz, 'baz')

    def test_precompute_required(self):
        model = self.env['test_orm.precompute.required']

        field = type(model).name
        self.assertTrue(field.related)
        self.assertTrue(field.store)
        self.assertTrue(field.required)

        partner = self.env['res.partner'].create({'name': 'Foo'})

        # this will crash if field is not precomputed
        record = model.create({'partner_id': partner.id})
        self.assertEqual(record.name, 'Foo')

        # check the queries being made
        QUERIES = [insert(model, 'partner_id', 'name')]
        with self.assertQueries(QUERIES):
            record = model.create({'partner_id': partner.id})

    def test_precompute_batch(self):
        model = self.env['test_orm.precompute.required']

        partners = self.env['res.partner'].create([
            {'name': name}
            for name in ["Foo", "Bar", "Baz"]
        ])

        # warmup
        model.create({'partner_id': partners[0].id})
        self.env.flush_all()
        self.env.invalidate_all()

        # check the number of queries: 1 SELECT + 1 INSERT
        with self.assertQueryCount(2):
            model.create([{'partner_id': pid} for pid in partners.ids])

    def test_precompute_monetary(self):
        """Make sure the rounding of monetaries correctly prefetches currency fields"""
        model = self.env['test_orm.precompute.monetary']
        currency = self.env['res.currency']

        # warmup
        model.create({})
        self.env.flush_all()
        self.env.invalidate_all()

        fnames = [fname for fname, field in currency._fields.items() if field.prefetch]
        QUERIES = [
            select(currency, *fnames),
            insert(model, 'amount', 'currency_id'),
            select(model, 'currency_id'),
        ]
        with self.assertQueries(QUERIES):
            model.create({})


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestModifiedPerformance(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Modified = cls.env['test_orm.modified']
        cls.ModifiedLine = cls.env['test_orm.modified.line']
        cls.modified_a = cls.Modified.create({
            'name': 'Test',
        })
        cls.modified_line_a = cls.ModifiedLine.create({
            'modified_id': cls.modified_a.id,
            'quantity': 5,
            'price': 1,
        })
        cls.modified_line_a_child = cls.ModifiedLine.create({
            'modified_id': cls.modified_a.id,
            'quantity': 5,
            'price': 2,
            'parent_id': cls.modified_line_a.id,
        })
        cls.modified_line_a_child_child = cls.ModifiedLine.create({
            'modified_id': cls.modified_a.id,
            'quantity': 5,
            'price': 3,
            'parent_id': cls.modified_line_a_child.id,
        })
        cls.env.invalidate_all()  # Clean the cache

    def test_modified_trigger_related(self):
        with self.assertQueryCount(0, flush=False):
            # No queries because `modified_name` has a empty cache
            self.modified_a.name = "Other"

        self.assertEqual(self.modified_line_a.modified_name, 'Other')  # check

    def test_modified_trigger_no_store_compute(self):
        with self.assertQueryCount(0, flush=False):
            # No queries because `total_quantity` has a empty cache
            self.modified_line_a.quantity = 8

        self.assertEqual(self.modified_a.total_quantity, 18)

    def test_modified_trigger_recursive_empty_cache(self):
        with self.assertQueryCount(0, flush=False):
            # No queries because `total_price` has a empty cache
            self.modified_line_a_child_child.price = 4

        self.assertEqual(self.modified_line_a.total_price, 7)
        self.assertEqual(self.modified_line_a.total_price_quantity, 35)
        self.assertEqual(self.modified_line_a_child.total_price, 6)
        self.assertEqual(self.modified_line_a_child.total_price_quantity, 30)

    def test_modified_trigger_recursive_fill_cache(self):
        self.assertEqual(self.modified_line_a.total_price, 6)
        self.assertEqual(self.modified_line_a.total_price_quantity, 30)
        with self.assertQueryCount(0, flush=False):
            # No query because the `modified_line_a.total_price` has fetch every data needed
            self.modified_line_a_child_child.price = 4

        self.assertEqual(self.modified_line_a.total_price_quantity, 35)
        self.assertEqual(self.modified_line_a.total_price, 7)

    def test_modified_trigger_recursive_partial_invalidate(self):
        self.assertEqual(self.modified_line_a_child.total_price_quantity, 25)
        self.modified_line_a_child_child.invalidate_recordset()

        self.modified_line_a_child.price
        with self.assertQueries(["""
            SELECT "test_orm_modified_line"."id",
                   "test_orm_modified_line"."modified_id",
                   "test_orm_modified_line"."quantity",
                   "test_orm_modified_line"."parent_id",
                   "test_orm_modified_line"."create_uid",
                   "test_orm_modified_line"."create_date"
            FROM "test_orm_modified_line"
            WHERE "test_orm_modified_line"."id" IN %s
        """], flush=False):
            self.modified_line_a_child_child.price = 4
        self.assertEqual(self.modified_line_a_child_child.total_price_quantity, 20)
        self.assertEqual(self.modified_line_a_child.total_price_quantity, 30)
        self.assertEqual(self.modified_line_a.total_price_quantity, 35)
        self.assertEqual(self.modified_line_a.total_price, 7)

    def test_modified_create_no_inverse(self):
        LinePositive = self.env['test_orm.modified.line.positive']
        LinePositive.create({}).is_positive  # warmup + fill cache of is_positive

        # One INSERT
        with self.assertQueryCount(1):
            self.ModifiedLine.create({})


@tagged('at_install', '-post_install')
class TestAttributes(TransactionCase):

    def test_we_cannot_add_attributes(self):
        Model = self.env['test_orm.category']
        instance = Model.create({'name': 'Foo'})

        with self.assertRaises(AttributeError):
            instance.unknown = 42
