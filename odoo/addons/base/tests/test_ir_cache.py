# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import marshal
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from odoo.tests.common import TransactionCase
from odoo.addons.base.models.ir_cache import _get_ir_cache_filename
from odoo.tools import SQL, config


class IrCacheCase(TransactionCase):
    """ The files of the entries in a temporary directory, with a canary. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # the rows are rolled back, not the files: not the directory of the
        # database (the GC deletes it when the canary of the database is
        # invalid, e.g. the cron did not run yet)
        cls.directory = os.path.join(cls.enterClassContext(tempfile.TemporaryDirectory()), 'db')
        cls.classPatch(config, 'cache_dir', lambda dbname: cls.directory)
        # no cron worker in the tests: add the canary like the cron triggered
        # by `_register_hook` (the invalid signatures are only reported with
        # a valid canary)
        cls.env['ir.cache']._gc_cache()


class TestIrCache(IrCacheCase):
    """ The API of `ir.cache`, with a version given as a string. """

    def rows(self, kind):
        # no ORM on `ir.cache` (`browse` is forbidden)
        return self.env.execute_query_dict(SQL(
            "SELECT id, key, version_data, version, create_date, signature FROM ir_cache WHERE kind = %s ORDER BY id",
            kind,
        ))

    def test_version_string(self):
        IrCache = self.env['ir.cache']
        IrCache._set__('test', 'k', b'value 1', version='v1')
        [row] = self.rows('test')
        self.assertEqual(row['version'], 'v1')
        self.assertEqual(row['version_data'], None)

        self.assertEqual(IrCache._lookup('test', 'k', 'v1'), b'value 1')
        self.assertIsNone(IrCache._lookup('test', 'k', 'v2'), "another version")
        self.assertIsNone(IrCache._lookup('test', 'k'), "the default version is ''")
        self.assertIsNone(IrCache._lookup('test', 'other', 'v1'), "another key")
        self.assertIsNone(IrCache._lookup('other', 'k', 'v1'), "another kind")

        # a new version: the last row wins, the previous one is not read anymore
        IrCache._set__('test', 'k', b'value 2', version='v2')
        self.assertEqual(len(self.rows('test')), 2)
        self.assertEqual(IrCache._lookup('test', 'k', 'v2'), b'value 2')
        self.assertIsNone(IrCache._lookup('test', 'k', 'v1'))

        # back to the previous version: a new row
        IrCache._set__('test', 'k', b'value 1 bis', version='v1')
        self.assertEqual(IrCache._lookup('test', 'k', 'v1'), b'value 1 bis')
        self.assertIsNone(IrCache._lookup('test', 'k', 'v2'))

    def test_version_default(self):
        IrCache = self.env['ir.cache']
        IrCache._set__('test', 'k', b'value')
        [row] = self.rows('test')
        self.assertEqual(row['version'], '')
        self.assertEqual(IrCache._lookup('test', 'k'), b'value')
        self.assertEqual(IrCache._lookup('test', 'k', ''), b'value')
        self.assertIsNone(IrCache._lookup('test', 'k', 'v1'))

    def test_version_string_multi(self):
        IrCache = self.env['ir.cache']
        IrCache._set__('test', 'a', b'a1', version='v1')
        IrCache._set__('test', 'b', b'b1', version='v1')
        IrCache._set__('test', 'c', b'c2', version='v2')
        self.assertEqual(IrCache._lookup_multi('test', ['a', 'b', 'c', 'd'], version='v1'), (b'a1', b'b1', None, None))
        self.assertEqual(IrCache._lookup_multi('test', ['c', 'a'], version='v2'), (b'c2', None), "in the order of the keys")
        self.assertEqual(IrCache._lookup_multi('test', [], version='v1'), ())

    def test_version_string_readonly(self):
        """ A read-only cursor inserts the rows after the commit, and reads
        them in the meantime, with the same version check. """
        IrCache = self.env['ir.cache']
        with patch.object(type(self.env.cr), 'readonly', property(lambda cr: True)):
            IrCache._set__('test', 'k', b'value 1', version='v1')
            IrCache._set__('test', 'other', b'other', version='v1')
            self.assertFalse(self.rows('test'), "inserted after the commit")
            self.assertEqual(IrCache._lookup('test', 'k', 'v1'), b'value 1')
            self.assertIsNone(IrCache._lookup('test', 'k', 'v2'))
            self.assertIsNone(IrCache._lookup('test', 'k'))
            self.assertEqual(IrCache._lookup_multi('test', ['other', 'k', 'none'], version='v1'), (b'other', b'value 1', None))

        # what the post-commit does, without a new cursor (it would commit)
        pending = self.env.cr.postcommit.data['ir.cache.pending'].rows__
        self.assertEqual(len(pending), 2)
        self.env.cr.postcommit.clear()
        self.env.cr.execute(SQL(
            "INSERT INTO ir_cache (create_date, kind, key, version_data, version, signature) VALUES %s",
            SQL(", ").join(SQL("(%s, %s, %s, %s, %s, %s)", *row) for row in pending),
        ))
        self.assertEqual(IrCache._lookup('test', 'k', 'v1'), b'value 1')
        self.assertIsNone(IrCache._lookup('test', 'k', 'v2'))

    def test_version_string_postcommit(self):
        """ The rows of a read-only cursor are inserted by the post-commit,
        with a new cursor (test cursors, like in a request). """
        with self.registry_test_mode():
            with self.registry.cursor(readonly=True) as cr:
                self.assertTrue(cr.readonly)
                IrCache = self.env(cr=cr)['ir.cache']
                IrCache._set__('test', 'k', b'value 1', version='v1')
                IrCache._set__('test', 'other', b'other', version='v1')
                self.assertFalse(self.rows('test'), "inserted after the commit")
                self.assertEqual(IrCache._lookup('test', 'k', 'v1'), b'value 1')

        self.assertEqual(len(self.rows('test')), 2, "inserted by the post-commit")
        IrCache = self.env['ir.cache']
        self.assertEqual(IrCache._lookup_multi('test', ['other', 'k'], version='v1'), (b'other', b'value 1'))
        self.assertIsNone(IrCache._lookup('test', 'k', 'v2'))

    def test_version_string_signature(self):
        """ The version is signed: a row whose version is changed to the
        requested one is read, and rejected. """
        IrCache = self.env['ir.cache']
        IrCache._set__('test', 'k', b'value', version='v1')
        [row] = self.rows('test')
        self.env.cr.execute(SQL("UPDATE ir_cache SET version = 'v2' WHERE id = %s", row['id']))
        with self.assertLogs('odoo.addons.base.models.ir_cache', 'INFO') as logs:
            self.assertIsNone(IrCache._lookup('test', 'k', 'v2'))
        self.assertIn("invalid signature", logs.output[0])
        self.assertIsNone(IrCache._lookup('test', 'k', 'v1'), "the row does not match anymore")

    def test_version_data_without_sql(self):
        """ A ``version_data`` needs the query computing the version from it:
        with a version given as a string, it is rejected, and nothing is
        stored. """
        IrCache = self.env['ir.cache']
        with self.assertRaises(ValueError):
            IrCache._set__('control', 'a', b'x', version_data=[1, 2], version='toto')
        self.assertFalse(self.rows('control'))
        self.assertIsNone(IrCache._lookup('control', 'a', 'toto'))

    def test_clear(self):
        IrCache = self.env['ir.cache']
        for key in ['(1, 2, x)', '(1, 22, x)', '(1, 3, x)', '(2, 2, x)', 'a_b', 'axb']:
            IrCache._set__('test', key, b'value')
        IrCache._set__('other', '(1, 2, x)', b'value')

        IrCache._clear('test', [])
        self.assertEqual(len(self.rows('test')), 6, "no prefix, nothing deleted")
        IrCache._clear('test', ['(1, 2, '])
        self.assertEqual([r['key'] for r in self.rows('test')], ['(1, 22, x)', '(1, 3, x)', '(2, 2, x)', 'a_b', 'axb'])
        IrCache._clear('test', ['a_', '(1, '])
        self.assertEqual([r['key'] for r in self.rows('test')], ['(2, 2, x)', 'axb'], "'_' is not a wildcard")
        self.assertEqual(len(self.rows('other')), 1, "another kind")
        IrCache._clear('test')
        self.assertFalse(self.rows('test'))
        self.assertEqual(len(self.rows('other')), 1, "another kind")
        self.assertTrue(IrCache._check_secret())

    def test_gc_file_kind_with_dash(self):
        """ A file whose kind contains '-' expires from the date at the end of
        its name, not from the first '-': otherwise it would never be
        collected and the filestore would grow forever. """
        # 20-digit timestamps (%Y%m%d%H%M%S%f), compared as strings to the GC limit
        old_file = Path(self.directory) / 'my-kind-19700101000000000000-abcd'
        new_file = Path(self.directory) / 'my-kind-29990101000000000000-abcd'
        old_file.write_bytes(b'x')
        new_file.write_bytes(b'x')
        self.env['ir.cache']._gc_cache()
        self.assertFalse(old_file.exists(), "an aged file with a '-' in its kind is collected")
        self.assertTrue(new_file.exists(), "a recent file is kept")

    def test_kind_path_traversal(self):
        """ A kind with a path separator would write out of the cache dir: it
        is rejected, when the name of the file is built. """
        with self.assertRaises(ValueError):
            _get_ir_cache_filename('../evil', datetime(2020, 1, 1), b'\xab')
        with self.assertRaises(ValueError):
            self.env['ir.cache']._set__('a/b', 'k', b'data')
        # nothing escaped the cache directory
        self.assertFalse(
            any('evil' in name or name == 'b' for name in os.listdir(os.path.dirname(self.directory))),
            "no file was written out of the cache directory",
        )


class TestQWebCodeCache(IrCacheCase):
    """ Compiled code shared through the `ir.cache` table. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        View = cls.env['ir.ui.view']
        cls.callee = View.create({
            'name': 'callee', 'type': 'qweb', 'key': 'base.test_code_cache_callee',
            'arch': '<span>callee</span>',
        })
        cls.caller = View.create({
            'name': 'caller', 'type': 'qweb', 'key': 'base.test_code_cache_caller',
            'arch': '<div><t t-call="base.test_code_cache_callee"/></div>',
        })

    def render(self, template, expected, generated, env=None, **context):
        """ Render the template like a new worker (only the `ir.cache` table)
        and check which templates were generated. """
        env = env or self.env
        env.transaction.invalidate_ormcache('templates')
        env.invalidate_all()

        refs = []
        origin_generate_code = env.registry['ir.qweb']._generate_code

        def _generate_code(self, template):
            refs.append(template)
            return origin_generate_code(self, template)

        with patch.object(env.registry['ir.qweb'], '_generate_code', _generate_code):
            self.assertEqual(str(env['ir.qweb'].with_context(**context)._render(template.id)), expected)
        self.assertEqual(sorted(refs), sorted(t.id for t in generated))

    def rows(self, template):
        # no ORM on `ir.cache` (`browse` is forbidden)
        return self.env.execute_query_dict(SQL(
            "SELECT id, key, version_data, create_date, signature FROM ir_cache WHERE kind = 'qweb' AND key LIKE %s ORDER BY id",
            f'(False, {template.id}, %',
        ))

    def path(self, row):
        """ Path of the file of the value of the row. """
        return os.path.join(self.directory, _get_ir_cache_filename('qweb', row['create_date'], bytes(row['signature'])))

    def test_reuse(self):
        self.render(self.caller, '<div><span>callee</span></div>', generated=self.caller + self.callee)
        self.assertEqual(len(self.rows(self.caller)), 1)
        self.render(self.caller, '<div><span>callee</span></div>', generated=[])
        self.assertEqual(len(self.rows(self.caller)), 1, "the valid row is used, no new row")

        # the value is in a file: without the file, the row is a miss
        os.unlink(self.path(self.rows(self.callee)[0]))
        with self.assertNoLogs('odoo.addons.base.models.ir_cache', 'INFO'):
            self.render(self.caller, '<div><span>callee</span></div>', generated=self.callee)
        self.assertEqual(len(self.rows(self.callee)), 2)
        self.render(self.caller, '<div><span>callee</span></div>', generated=[])

    def test_readonly(self):
        """ A read-only cursor inserts the rows after the commit, and reads
        them in the meantime. """
        with patch.object(type(self.env.cr), 'readonly', property(lambda cr: True)):
            self.render(self.caller, '<div><span>callee</span></div>', generated=self.caller + self.callee)
            self.assertFalse(self.rows(self.caller), "inserted after the commit")
            self.render(self.caller, '<div><span>callee</span></div>', generated=[])

        # what the post-commit does, without a new cursor (it would commit)
        pending = self.env.cr.postcommit.data['ir.cache.pending'].rows__
        self.assertEqual(len(pending), 2, "generated once")
        self.env.cr.postcommit.clear()
        self.env.cr.execute(SQL(
            "INSERT INTO ir_cache (create_date, kind, key, version_data, version, signature) VALUES %s",
            SQL(", ").join(SQL("(%s, %s, %s, %s, %s, %s)", *row) for row in pending),
        ))
        self.render(self.caller, '<div><span>callee</span></div>', generated=[])
        self.callee.arch = '<span>callee 2</span>'
        self.render(self.caller, '<div><span>callee 2</span></div>', generated=self.callee)

    def test_readonly_postcommit(self):
        """ The rows of a read-only cursor are inserted by the post-commit,
        with a new cursor (test cursors, like in a request). """
        with self.registry_test_mode():
            with self.registry.cursor(readonly=True) as cr:
                self.assertTrue(cr.readonly)
                env = self.env(cr=cr)
                self.render(self.caller, '<div><span>callee</span></div>', generated=self.caller + self.callee, env=env)
                self.assertFalse(self.rows(self.caller), "inserted after the commit")
                self.render(self.caller, '<div><span>callee</span></div>', generated=[], env=env)

        self.assertEqual(len(self.rows(self.caller)), 1, "inserted by the post-commit")
        self.assertEqual(len(self.rows(self.callee)), 1, "inserted by the post-commit")
        self.render(self.caller, '<div><span>callee</span></div>', generated=[])
        self.callee.arch = '<span>callee 2</span>'
        self.render(self.caller, '<div><span>callee 2</span></div>', generated=self.callee)

    def test_invalidation(self):
        self.render(self.caller, '<div><span>callee</span></div>', generated=self.caller + self.callee)

        # the t-call is resolved when rendering: only the callee is generated
        self.callee.arch = '<span>callee 2</span>'
        self.render(self.caller, '<div><span>callee 2</span></div>', generated=self.callee)
        self.assertEqual(len(self.rows(self.callee)), 1, "the old row is deleted by the write")
        self.assertEqual(len(self.rows(self.caller)), 1, "another inheritance tree, kept")

        # a new view inheriting from the template, even inactive
        extension = self.env['ir.ui.view'].create({
            'name': 'extension', 'type': 'qweb', 'mode': 'extension', 'active': False,
            'inherit_id': self.caller.id, 'arch': '<xpath expr="//div" position="inside"><b/></xpath>',
        })
        self.render(self.caller, '<div><span>callee 2</span></div>', generated=self.caller)
        self.render(self.caller, '<div><span>callee 2</span></div>', generated=[])

        # activation
        extension.active = True
        self.render(self.caller, '<div><span>callee 2</span><b></b></div>', generated=self.caller)

        # deletion
        extension.unlink()
        self.render(self.caller, '<div><span>callee 2</span></div>', generated=self.caller)

        # back to a previous version: a new row (the last one is used)
        self.callee.arch = '<span>callee</span>'
        self.render(self.caller, '<div><span>callee</span></div>', generated=self.callee)
        self.render(self.caller, '<div><span>callee</span></div>', generated=[])

        # other options (cache keys), other rows
        self.render(self.caller, '<div><span>callee</span></div>', generated=self.caller + self.callee, preserve_comments=True)
        self.render(self.caller, '<div><span>callee</span></div>', generated=[], preserve_comments=True)

        # the garbage collector deletes the old rows only (e.g. the compiler
        # was fixed in the meantime)
        self.assertEqual(len(self.rows(self.callee)), 2)
        self.env['ir.cache']._gc_cache()
        self.assertEqual(len(self.rows(self.callee)), 2)
        old_rows = self.rows(self.callee)
        self.env.cr.execute(SQL("UPDATE ir_cache SET create_date = create_date - interval '8 days' WHERE id = ANY(%s)", [r['id'] for r in old_rows]))
        self.env['ir.cache']._gc_cache()
        self.assertFalse(self.rows(self.callee))
        self.render(self.caller, '<div><span>callee</span></div>', generated=self.callee)

        # the files expire like the rows, from the date in their name (whether
        # their row was deleted or not, e.g. rolled back), except the canary
        def aged(kind, row):
            """ Rename the file of the row as created 8 days earlier. """
            create_date = row['create_date'] - timedelta(days=8)
            path = os.path.join(self.directory, _get_ir_cache_filename(kind, create_date, bytes(row['signature'])))
            os.rename(os.path.join(self.directory, _get_ir_cache_filename(kind, row['create_date'], bytes(row['signature']))), path)
            return path

        self.assertTrue(all(os.path.exists(self.path(row)) for row in old_rows))
        old_paths = [aged('qweb', row) for row in old_rows]
        [canary] = self.env.execute_query_dict(SQL("SELECT id, create_date, signature FROM ir_cache WHERE kind = 'ir_cache'"))
        canary_path = aged('ir_cache', canary)
        # the row is rolled back, not the file (shared by the class)
        self.addCleanup(os.rename, canary_path, os.path.join(self.directory, _get_ir_cache_filename('ir_cache', canary['create_date'], bytes(canary['signature']))))
        self.env.cr.execute(SQL("UPDATE ir_cache SET create_date = create_date - interval '8 days' WHERE id = %s", canary['id']))
        self.env['ir.cache']._gc_cache()
        self.assertTrue(os.path.exists(canary_path))
        self.assertFalse(any(map(os.path.exists, old_paths)))
        self.assertTrue(all(map(os.path.exists, map(self.path, self.rows(self.caller) + self.rows(self.callee)))))
        self.assertTrue(self.env['ir.cache']._check_secret(), "the canary does not expire")
        self.render(self.caller, '<div><span>callee</span></div>', generated=[])

    def test_key_of_the_template(self):
        """ The code of a template is never stored under the key of another
        template: the caller of `_generate_code_uncached` (e.g. a server
        action) does not give the key, else that code would be rendered
        instead of the other template, even after a change of the latter. """
        other = self.env['ir.ui.view'].create({
            'name': 'other', 'type': 'qweb', 'key': 'base.test_code_cache_other',
            'arch': '<i>other</i>',
        })
        IrQweb = self.env['ir.qweb']
        self.render(self.callee, '<span>callee</span>', generated=self.callee)
        # the second argument used to be the key of the entry
        IrQweb._generate_code_uncached(other.id, repr(IrQweb._get_cache_key(self.callee.id)))
        self.assertEqual(len(self.rows(self.callee)), 1)
        self.assertEqual(len(self.rows(other)), 1, "stored under its own key")
        self.render(self.callee, '<span>callee</span>', generated=[])
        self.callee.arch = '<span>callee 2</span>'
        self.render(self.callee, '<span>callee 2</span>', generated=self.callee)

    def test_query_count_hot(self):
        """ A new transaction in a warm worker: the ormcaches are filled, the
        compiled code (of the template and of its t-calls) is read from
        `ir.cache`. """
        IrQweb = self.env['ir.qweb']
        self.render(self.caller, '<div><span>callee</span></div>', generated=self.caller + self.callee)
        IrQweb._render(self.caller.id)

        # what a new transaction does not have: the caches of the cursor and
        # of the records
        self.env.cr.cache.clear()
        self.env.invalidate_all()
        ir_cache_lookup = """
            WITH entry AS MATERIALIZED (
                SELECT DISTINCT ON (key) key, version_data, version, create_date, signature
                FROM ir_cache
                WHERE kind = %s AND key = ANY(%s)
                ORDER BY key, id DESC
            ), ...
        """
        with self.assertQueries([
            # the code of the template
            ir_cache_lookup,
            # the code of the t-calls, in batch (their ids are in the ormcache)
            ir_cache_lookup,
        ]):
            self.assertEqual(str(IrQweb._render(self.caller.id)), '<div><span>callee</span></div>')

    def test_query_count_cold(self):
        """ A new worker: the ormcaches are empty, the compiled code is in
        `ir.cache`. The t-calls are resolved in batch, by key and by xmlid
        (a view whose xmlid is not its key, found in `ir.model.data`). """
        View = self.env['ir.ui.view']
        callee_data = View.create({
            'name': 'callee data', 'type': 'qweb', 'arch': '<b>data</b>',
        })
        self.env['ir.model.data'].create({
            'module': 'base', 'name': 'test_code_cache_callee_data',
            'model': 'ir.ui.view', 'res_id': callee_data.id,
        })
        other = View.create({
            'name': 'other', 'type': 'qweb', 'key': 'base.test_code_cache_other',
            'arch': '<i>other</i>',
        })
        caller = View.create({
            'name': 'caller 2', 'type': 'qweb', 'key': 'base.test_code_cache_caller_2',
            'arch': '<div>'
                '<t t-call="base.test_code_cache_callee"/>'
                '<t t-call="base.test_code_cache_other"/>'
                '<t t-call="base.test_code_cache_callee_data"/>'
            '</div>',
        })
        expected = '<div><span>callee</span><i>other</i><b>data</b></div>'
        self.render(caller, expected, generated=caller + self.callee + other + callee_data)

        # a new worker: no ormcache, no cache of the cursor and of the records
        self.env.transaction.invalidate_ormcache('templates')
        self.env.cr.cache.clear()
        self.env.invalidate_all()
        view_fields = (
            '"ir_ui_view"."id", "ir_ui_view"."name", "ir_ui_view"."model", "ir_ui_view"."key", '
            '"ir_ui_view"."priority", "ir_ui_view"."type", "ir_ui_view"."arch_db"->>%s, '
            '"ir_ui_view"."arch_fs", "ir_ui_view"."arch_updated", "ir_ui_view"."arch_prev", '
            '"ir_ui_view"."inherit_id", "ir_ui_view"."mode", "ir_ui_view"."notes", "ir_ui_view"."active", '
            '"ir_ui_view"."technical_usage", "ir_ui_view"."create_uid", "ir_ui_view"."create_date", '
            '"ir_ui_view"."write_uid", "ir_ui_view"."write_date", "ir_ui_view"."customize_show"'
        )
        ir_cache_lookup = """
            WITH entry AS MATERIALIZED (
                SELECT DISTINCT ON (key) key, version_data, version, create_date, signature
                FROM ir_cache
                WHERE kind = %s AND key = ANY(%s)
                ORDER BY key, id DESC
            ), ...
        """
        with self.assertQueries([
            # the template, rendered by id
            f'SELECT {view_fields} FROM "ir_ui_view" WHERE "ir_ui_view"."id" IN %s',
            # the code of the template
            ir_cache_lookup,
            # the t-calls in batch: by key...
            f'''SELECT {view_fields} FROM "ir_ui_view"
               WHERE ("ir_ui_view"."active" IS TRUE AND "ir_ui_view"."key" IN %s)
               ORDER BY "ir_ui_view"."priority", "ir_ui_view"."id"''',
            # ... and by xmlid (the view without key)
            '''SELECT "ir_model_data"."id", "ir_model_data"."module", "ir_model_data"."name", "ir_model_data"."res_id"
               FROM "ir_model_data"
               WHERE ("ir_model_data"."model" IN %s AND "ir_model_data"."module" IN %s AND "ir_model_data"."name" IN %s)
               ORDER BY "ir_model_data"."module", "ir_model_data"."model", "ir_model_data"."name"''',
            f'''SELECT {view_fields} FROM "ir_ui_view"
               WHERE "ir_ui_view"."id" IN %s
               ORDER BY "ir_ui_view"."priority", "ir_ui_view"."name", "ir_ui_view"."id"''',
            # the code of the t-calls, in batch
            ir_cache_lookup,
        ]):
            self.assertEqual(str(self.env['ir.qweb']._render(caller.id)), expected)

    def test_python_version(self):
        """ The code objects are not portable between versions of python: the
        version is in the key, the entries of each version are kept side by
        side (e.g. two servers sharing the database during a deployment). """
        self.render(self.callee, '<span>callee</span>', generated=self.callee)
        with patch('odoo.addons.base.models.ir_qweb.MAGIC_NUMBER', b'\xff\xff\r\n'):
            self.render(self.callee, '<span>callee</span>', generated=self.callee)
            self.render(self.callee, '<span>callee</span>', generated=[])
        self.assertEqual(len(self.rows(self.callee)), 2)
        self.render(self.callee, '<span>callee</span>', generated=[])

    def test_dev_mode_from_config(self):
        """ The compiled code is shared by the callers with the same key: what
        is not in the key (e.g. `dev_mode`, for `t-debug`) does not come from
        the context of the caller. """
        debug = self.env['ir.ui.view'].create({
            'name': 'debug', 'type': 'qweb', 'key': 'base.test_code_cache_debug',
            'arch': '<span t-debug="">debug</span>',
        })
        with patch.object(self.env.registry['ir.qweb'], '_debug_trace') as debug_trace, \
                self.assertLogs('odoo.addons.base.models.ir_qweb', 'WARNING'):
            self.env['ir.qweb'].with_context(dev_mode=True)._generate_code_cached(debug.id)
            self.render(debug, '<span>debug</span>', generated=[])
        debug_trace.assert_not_called()

    def test_signature(self):
        """ The bytecode of the table is executed: whoever writes in the table,
        only the rows signed by this server are used. """
        self.render(self.caller, '<div><span>callee</span></div>', generated=self.caller + self.callee)
        [row] = self.rows(self.callee)
        evil = marshal.dumps(('', {}, 'evil', compile('raise Exception("evil")', '<evil>', 'exec')))

        def forge(data=None, **values):
            """ Copy the row of the callee with ``values`` (as the last row),
            with a file containing ``data``. """
            if data is not None:
                values['create_date'] = row['create_date'] + timedelta(seconds=1)
                Path(self.path({**row, **values})).write_bytes(data)
            columns = ['create_date', 'kind', 'key', 'version_data', 'version', 'signature']
            self.env.cr.execute(SQL(
                "INSERT INTO ir_cache (%s) SELECT %s FROM ir_cache WHERE id = %s",
                SQL(', ').join(map(SQL.identifier, columns)),
                SQL(', ').join(SQL('%s', values[c]) if c in values else SQL.identifier(c) for c in columns),
                row['id'],
            ))

        def check_forged(generated, data=None, **values):
            with self.env.cr.savepoint(flush=False) as savepoint:
                forge(data=data, **values)
                with self.assertLogs('odoo.addons.base.models.ir_cache', 'INFO'):
                    self.render(self.caller, '<div><span>callee</span></div>', generated=generated)
                savepoint.rollback()

        # a version_data: not used by qweb, but signed
        other_data = json.dumps({'x': 1})

        # the payload, the version_data, or the key (the row of another
        # template)
        check_forged(self.callee, data=evil)
        check_forged(self.callee, version_data=other_data)
        check_forged(self.caller, key=self.rows(self.caller)[0]['key'])
        # a row whose version does not match its source is not even read
        with self.env.cr.savepoint(flush=False) as savepoint:
            forge(version='x', data=evil)
            with self.assertNoLogs('odoo.addons.base.models.ir_cache', 'INFO'):
                self.render(self.caller, '<div><span>callee</span></div>', generated=self.callee)
            savepoint.rollback()
        # the row itself modified, not a copy
        with self.assertLogs('odoo.addons.base.models.ir_cache', 'INFO'):
            self.env.cr.execute(SQL("UPDATE ir_cache SET version_data = %s WHERE id = %s", other_data, row['id']))
            self.render(self.caller, '<div><span>callee</span></div>', generated=self.callee)

        # a new signed row is added and used
        self.render(self.caller, '<div><span>callee</span></div>', generated=[])
        self.assertEqual(len(self.rows(self.callee)), 2)

    def test_key_change(self):
        """ The rows signed with another key (another server secret,
        database or version) are ignored without a warning per row, and all
        deleted at once by the cron. """
        IrCache = self.env['ir.cache']
        cron = self.env.ref('base.ir_cron_ir_cache_gc')
        # the files are deleted with the rows: not those of the class (the
        # canary of the class would lose its file)
        directory = os.path.join(self.enterContext(tempfile.TemporaryDirectory()), 'db')
        self.patch(config, 'cache_dir', lambda dbname: directory)
        IrCache._gc_cache()  # the canary in this directory
        self.render(self.caller, '<div><span>callee</span></div>', generated=self.caller + self.callee)

        def canaries():
            return [id_ for [id_] in self.env.execute_query(SQL("SELECT id FROM ir_cache WHERE kind = 'ir_cache' AND key = 'ir.cache'"))]

        def triggers():
            """ Number of triggers of the cron added by the test. """
            return self.env['ir.cron.trigger'].search_count([('cron_id', '=', cron.id)]) - initial_triggers

        initial_triggers = 0
        initial_triggers = triggers()

        # `server_secret` is a cached property: another value in the cache
        with patch.dict(config.__dict__, server_secret=b'other secret'.ljust(32, b'\0')):
            # the canary is signed with the old key too: the rows are
            # ignored, without a warning
            with self.assertNoLogs('odoo.addons.base.models.ir_cache', 'WARNING'):
                self.render(self.caller, '<div><span>callee</span></div>', generated=self.caller + self.callee)
            self.assertEqual(len(self.rows(self.caller)), 2, "the rows of the old key are kept until the cron")

            # detected when starting the server: the cron is triggered
            with self.assertLogs('odoo.addons.base.models.ir_cache', 'INFO') as logs:
                IrCache._register_hook()
            self.assertEqual(len(logs.output), 1)
            self.assertIn("the key of the signatures changed", logs.output[0])
            self.assertEqual(triggers(), 1)

            # the cron deletes all the rows and their files, and adds a new
            # canary
            old_files = os.listdir(directory)
            IrCache._gc_cache()
            self.assertFalse(self.rows(self.caller))
            self.assertEqual(len(canaries()), 1)
            [canary_file] = os.listdir(directory)
            self.assertNotIn(canary_file, old_files)
            self.assertTrue(IrCache._check_secret())
            with self.assertNoLogs('odoo.addons.base.models.ir_cache', 'WARNING'):
                self.render(self.caller, '<div><span>callee</span></div>', generated=self.caller + self.callee)
                self.render(self.caller, '<div><span>callee</span></div>', generated=[])
                IrCache._register_hook()
            self.assertEqual(triggers(), 1, "valid canary, the cron is not triggered")

            # the canary does not expire
            self.env.cr.execute(SQL("UPDATE ir_cache SET create_date = create_date - interval '8 days'"))
            IrCache._gc_cache()
            self.assertEqual(len(canaries()), 1)
            self.assertFalse(self.rows(self.caller))

            # without canary, the cron is not triggered
            self.env.cr.execute(SQL("DELETE FROM ir_cache WHERE id = ANY(%s)", canaries()))
            IrCache._register_hook()
            self.assertEqual(triggers(), 2)
            IrCache._gc_cache()
            self.assertEqual(len(canaries()), 1)
