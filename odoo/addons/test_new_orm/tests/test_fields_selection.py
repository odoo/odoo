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


@tagged('selection_abstract')
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestSelectionDeleteUpdate(TransactionCase):

    MODEL_ABSTRACT = 'test_orm.state_mixin'

    def setUp(self):
        super().setUp()
        # enable unlinking ir.model.fields.selection
        self.patch(self.registry, 'ready', False)

    def test_unlink_asbtract(self):
        self.env['ir.model.fields.selection'].search([
            ('field_id.model', '=', self.MODEL_ABSTRACT),
            ('field_id.name', '=', 'state'),
            ('value', '=', 'confirmed'),
        ], limit=1).unlink()


@tagged('selection_update_base')
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestSelectionUpdates(TransactionCase):
    MODEL_BASE = 'test_orm.model_selection_base'
    MODEL_RELATED = 'test_orm.model_selection_related'
    MODEL_RELATED_UPDATE = 'test_orm.model_selection_related_updatable'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Specifying a lang in env/context should not increase query counts
        # of CRUD operations
        cls.env = cls.env(context={'lang': 'en_US'})

    def test_selection(self):
        self.env[self.MODEL_BASE].create({})   # warming up
        with self.assertQueryCount(1):
            self.env[self.MODEL_BASE].create({})
        with self.assertQueryCount(1):
            record = self.env[self.MODEL_BASE].create({'my_selection': 'foo'})
        with self.assertQueryCount(1):
            record.my_selection = 'bar'

    def test_selection_related_readonly(self):
        related_record = self.env[self.MODEL_BASE].create({'my_selection': 'foo'})
        with self.assertQueryCount(2):  # defaults (readonly related field), INSERT
            record = self.env[self.MODEL_RELATED].create({'selection_id': related_record.id})
        with self.assertQueryCount(0):
            record.related_selection = 'bar'

    def test_selection_related(self):
        related_record = self.env[self.MODEL_BASE].create({'my_selection': 'foo'})
        with self.assertQueryCount(2):  # defaults (related field), INSERT
            record = self.env[self.MODEL_RELATED_UPDATE].create({'selection_id': related_record.id})
        with self.assertQueryCount(2):
            record.related_selection = 'bar'


@tagged('selection_ondelete_base')
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestSelectionOndelete(TransactionCase):

    MODEL_BASE = 'test_orm.model_selection_base'
    MODEL_REQUIRED = 'test_orm.model_selection_required'
    MODEL_NONSTORED = 'test_orm.model_selection_non_stored'
    MODEL_WRITE_OVERRIDE = 'test_orm.model_selection_required_for_write_override'

    def setUp(self):
        super().setUp()
        # enable unlinking ir.model.fields.selection
        self.patch(self.registry, 'ready', False)

    def _unlink_option(self, model, option):
        self.env['ir.model.fields.selection'].search([
            ('field_id.model', '=', model),
            ('field_id.name', '=', 'my_selection'),
            ('value', '=', option),
        ], limit=1).unlink()

    def test_ondelete_default(self):
        # create some records, one of which having the extended selection option
        rec1 = self.env[self.MODEL_REQUIRED].create({'my_selection': 'foo'})
        rec2 = self.env[self.MODEL_REQUIRED].create({'my_selection': 'bar'})
        rec3 = self.env[self.MODEL_REQUIRED].create({'my_selection': 'baz'})

        # test that all values are correct before the removal of the value
        self.assertEqual(rec1.my_selection, 'foo')
        self.assertEqual(rec2.my_selection, 'bar')
        self.assertEqual(rec3.my_selection, 'baz')

        # unlink the extended option (simulates a module uninstall)
        self._unlink_option(self.MODEL_REQUIRED, 'baz')

        # verify that the ondelete policy has succesfully been applied
        self.assertEqual(rec1.my_selection, 'foo')
        self.assertEqual(rec2.my_selection, 'bar')
        self.assertEqual(rec3.my_selection, 'foo')   # reset to default

    def test_ondelete_base_null_explicit(self):
        rec1 = self.env[self.MODEL_BASE].create({'my_selection': 'foo'})
        rec2 = self.env[self.MODEL_BASE].create({'my_selection': 'bar'})
        rec3 = self.env[self.MODEL_BASE].create({'my_selection': 'quux'})

        self.assertEqual(rec1.my_selection, 'foo')
        self.assertEqual(rec2.my_selection, 'bar')
        self.assertEqual(rec3.my_selection, 'quux')

        self._unlink_option(self.MODEL_BASE, 'quux')

        self.assertEqual(rec1.my_selection, 'foo')
        self.assertEqual(rec2.my_selection, 'bar')
        self.assertFalse(rec3.my_selection)

    def test_ondelete_base_null_implicit(self):
        rec1 = self.env[self.MODEL_BASE].create({'my_selection': 'foo'})
        rec2 = self.env[self.MODEL_BASE].create({'my_selection': 'bar'})
        rec3 = self.env[self.MODEL_BASE].create({'my_selection': 'ham'})

        self.assertEqual(rec1.my_selection, 'foo')
        self.assertEqual(rec2.my_selection, 'bar')
        self.assertEqual(rec3.my_selection, 'ham')

        self._unlink_option(self.MODEL_BASE, 'ham')

        self.assertEqual(rec1.my_selection, 'foo')
        self.assertEqual(rec2.my_selection, 'bar')
        self.assertFalse(rec3.my_selection)

    def test_ondelete_cascade(self):
        rec1 = self.env[self.MODEL_REQUIRED].create({'my_selection': 'foo'})
        rec2 = self.env[self.MODEL_REQUIRED].create({'my_selection': 'bar'})
        rec3 = self.env[self.MODEL_REQUIRED].create({'my_selection': 'eggs'})

        self.assertEqual(rec1.my_selection, 'foo')
        self.assertEqual(rec2.my_selection, 'bar')
        self.assertEqual(rec3.my_selection, 'eggs')

        self._unlink_option(self.MODEL_REQUIRED, 'eggs')

        self.assertEqual(rec1.my_selection, 'foo')
        self.assertEqual(rec2.my_selection, 'bar')
        self.assertFalse(rec3.exists())

    def test_ondelete_literal(self):
        rec1 = self.env[self.MODEL_REQUIRED].create({'my_selection': 'foo'})
        rec2 = self.env[self.MODEL_REQUIRED].create({'my_selection': 'bar'})
        rec3 = self.env[self.MODEL_REQUIRED].create({'my_selection': 'bacon'})

        self.assertEqual(rec1.my_selection, 'foo')
        self.assertEqual(rec2.my_selection, 'bar')
        self.assertEqual(rec3.my_selection, 'bacon')

        self._unlink_option(self.MODEL_REQUIRED, 'bacon')

        self.assertEqual(rec1.my_selection, 'foo')
        self.assertEqual(rec2.my_selection, 'bar')
        self.assertEqual(rec3.my_selection, 'bar')

    def test_ondelete_multiple_explicit(self):
        rec1 = self.env[self.MODEL_REQUIRED].create({'my_selection': 'foo'})
        rec2 = self.env[self.MODEL_REQUIRED].create({'my_selection': 'eevee'})
        rec3 = self.env[self.MODEL_REQUIRED].create({'my_selection': 'pikachu'})

        self.assertEqual(rec1.my_selection, 'foo')
        self.assertEqual(rec2.my_selection, 'eevee')
        self.assertEqual(rec3.my_selection, 'pikachu')

        self._unlink_option(self.MODEL_REQUIRED, 'eevee')
        self._unlink_option(self.MODEL_REQUIRED, 'pikachu')

        self.assertEqual(rec1.my_selection, 'foo')
        self.assertEqual(rec2.my_selection, 'bar')
        self.assertEqual(rec3.my_selection, 'foo')

    def test_ondelete_callback(self):
        rec = self.env[self.MODEL_REQUIRED].create({'my_selection': 'knickers'})

        self.assertEqual(rec.my_selection, 'knickers')

        self._unlink_option(self.MODEL_REQUIRED, 'knickers')

        self.assertEqual(rec.my_selection, 'foo')
        self.assertFalse(rec.active)

    def test_non_stored_selection(self):
        rec = self.env[self.MODEL_NONSTORED].create({})
        rec.my_selection = 'foo'

        self.assertEqual(rec.my_selection, 'foo')

        self._unlink_option(self.MODEL_NONSTORED, 'foo')

        self.assertFalse(rec.my_selection)

    def test_required_base_selection_field(self):
        # test that no ondelete action is executed on a required selection field that is not
        # extended, only required fields that extend it with selection_add should
        # have ondelete actions defined
        rec = self.env[self.MODEL_REQUIRED].create({'my_selection': 'foo'})
        self.assertEqual(rec.my_selection, 'foo')

        self._unlink_option(self.MODEL_REQUIRED, 'foo')
        self.assertEqual(rec.my_selection, 'foo')

    @mute_logger('odoo.addons.base.models.ir_model')
    def test_write_override_selection(self):
        # test that on override to write that raises an error does not prevent the ondelete
        # policy from executing and cleaning up what needs to be cleaned up
        rec = self.env[self.MODEL_WRITE_OVERRIDE].create({'my_selection': 'divinity'})
        self.assertEqual(rec.my_selection, 'divinity')

        self._unlink_option(self.MODEL_WRITE_OVERRIDE, 'divinity')
        self.assertEqual(rec.my_selection, 'foo')


@tagged('selection_ondelete_advanced')
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestSelectionOndeleteAdvanced(TransactionCase):

    MODEL_BASE = 'test_orm.model_selection_base'
    MODEL_REQUIRED = 'test_orm.model_selection_required'

    def setUp(self):
        super().setUp()
        # necessary cleanup for resetting changes in the registry
        for model_name in (self.MODEL_BASE, self.MODEL_REQUIRED):
            Model = self.registry[model_name]
            self.addCleanup(setattr, Model, '_base_classes__', Model._base_classes__)

    def test_ondelete_unexisting_policy(self):
        from odoo.orm.model_classes import add_to_registry  # noqa: PLC0415

        class Foo(models.Model):
            _module = None
            _name = self.MODEL_REQUIRED
            _inherit = [self.MODEL_REQUIRED]

            my_selection = fields.Selection(selection_add=[
                ('random', "Random stuff"),
            ], ondelete={'random': 'poop'})

        add_to_registry(self.registry, Foo)

        with self.assertRaises(ValueError):
            self.registry._setup_models__(self.env.cr, [])  # incremental setup

    def test_ondelete_default_no_default(self):
        from odoo.orm.model_classes import add_to_registry  # noqa: PLC0415

        class Foo(models.Model):
            _module = None
            _name = self.MODEL_BASE
            _inherit = [self.MODEL_BASE]

            my_selection = fields.Selection(selection_add=[
                ('corona', "Corona beers suck"),
            ], ondelete={'corona': 'set default'})

        add_to_registry(self.registry, Foo)

        with self.assertRaises(AssertionError):
            self.registry._setup_models__(self.env.cr, [])  # incremental setup

    def test_ondelete_value_no_valid(self):
        from odoo.orm.model_classes import add_to_registry  # noqa: PLC0415

        class Foo(models.Model):
            _module = None
            _name = self.MODEL_BASE
            _inherit = [self.MODEL_BASE]

            my_selection = fields.Selection(selection_add=[
                ('westvleteren', "Westvleteren beers is overrated"),
            ], ondelete={'westvleteren': 'set foooo'})

        add_to_registry(self.registry, Foo)

        with self.assertRaises(AssertionError):
            self.registry._setup_models__(self.env.cr, [])  # incremental setup

    def test_ondelete_required_null_explicit(self):
        from odoo.orm.model_classes import add_to_registry  # noqa: PLC0415

        class Foo(models.Model):
            _module = None
            _name = self.MODEL_REQUIRED
            _inherit = [self.MODEL_REQUIRED]

            my_selection = fields.Selection(selection_add=[
                ('brap', "Brap"),
            ], ondelete={'brap': 'set null'})

        add_to_registry(self.registry, Foo)

        with self.assertRaises(ValueError):
            self.registry._setup_models__(self.env.cr, [])  # incremental setup

    def test_ondelete_required_null_implicit(self):
        from odoo.orm.model_classes import add_to_registry  # noqa: PLC0415

        class Foo(models.Model):
            _module = None
            _name = self.MODEL_REQUIRED
            _inherit = [self.MODEL_REQUIRED]

            my_selection = fields.Selection(selection_add=[
                ('boing', "Boyoyoyoing"),
            ])

        add_to_registry(self.registry, Foo)

        with self.assertRaises(ValueError):
            self.registry._setup_models__(self.env.cr, [])  # incremental setup
