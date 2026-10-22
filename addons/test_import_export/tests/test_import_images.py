import base64
import csv
import io

from PIL import Image

from odoo.tests.common import TransactionCase
from odoo.tools import BinaryBytes

from unittest.mock import patch


def make_png(color):
    """Return (raw bytes, base64 string) of a tiny 1x1 PNG of the given color."""
    buf = io.BytesIO()
    Image.new('RGB', (1, 1), color).save(buf, format='PNG')
    raw = buf.getvalue()
    return raw, base64.b64encode(raw).decode()


PNG_RED, B64_RED = make_png('#FF0000')
PNG_BLUE, B64_BLUE = make_png('#0000FF')


class ImportImagesCommon(TransactionCase):
    """Common tooling to simulate the two-phase import of binary files.

    Phase 1: ``execute_import`` on ``base_import.import``, exactly like the
    import screen does. The cells containing file names are detected by the
    server which returns the list of binary files it could not import inline
    (through ``binary_filenames``), one entry per file, pointing at the record
    each file must be written to.

    Phase 2: for each returned entry the client uploads the matching file
    content with a ``load`` call on the target record, exactly like
    ``BinaryFileManager`` does in the import screen.
    """

    def _execute_import(self, res_model, fields, rows, options=None, dryrun=False):
        f = io.StringIO()
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(fields)
        writer.writerows(rows)
        import_wizard = self.env['base_import.import'].create({
            'res_model': res_model,
            'file': BinaryBytes(f.getvalue().encode()),
            'file_type': 'text/csv',
        })
        return import_wizard.execute_import(
            fields,
            [],
            {'has_headers': True, 'separator': ',', 'quoting': '"', **(options or {})},
            dryrun=dryrun,
        )

    def _push_files(self, result, files):
        """Phase 2: upload the local files on the records returned by phase 1."""
        for entry in result['binary_filenames']:
            if entry['name'] not in files:
                continue
            self.env[entry['model']].with_context(import_file=True).load(
                ['.id', entry['field']],
                [[entry['id'], files[entry['name']]]],
            )

    def _import_with_files(self, res_model, fields, rows, files, options=None):
        result = self._execute_import(res_model, fields, rows, options)
        self._push_files(result, files)
        return result


class TestImportUploadedImages(ImportImagesCommon):
    def test_top_level_image(self):
        """A plain binary column: the file must land on the imported record."""
        result = self._import_with_files(
            'res.partner',
            ['name', 'image_1920'],
            [['Partner A', 'a.png']],
            {'a.png': B64_RED},
        )
        partner = self.env['res.partner'].search([('name', '=', 'Partner A')])
        self.assertEqual(len(partner), 1)
        self.assertEqual(partner.image_1920.content, PNG_RED)
        self.assertEqual(result['binary_filenames'], [
            {'model': 'res.partner', 'id': partner.id, 'field': 'image_1920', 'name': 'a.png'},
        ])

    def test_two_records_one_image_each(self):
        """One row per record: each file must go to its own record."""
        result = self._import_with_files(
            'res.partner',
            ['name', 'image_1920'],
            [['Partner A', 'a.png'], ['Partner B', 'b.png']],
            {'a.png': B64_RED, 'b.png': B64_BLUE},
        )
        partner_a, partner_b = self.env['res.partner'].search([('name', 'in', ['Partner A', 'Partner B'])], order='name')
        self.assertEqual(partner_a.image_1920.content, PNG_RED)
        self.assertEqual(partner_b.image_1920.content, PNG_BLUE)
        self.assertEqual(
            sorted(entry['name'] for entry in result['binary_filenames']),
            ['a.png', 'b.png'],
        )

    def test_o2m_images(self):
        """Replica of the product extra images import: the files must be
        written on the co-model sub-records created in phase 1."""
        result = self._import_with_files(
            'import.o2m',
            ['name', 'value/name', 'value/image'],
            [
                ['O2M Parent', 'Child 1', 'c1.png'],
                ['', 'Child 2', 'c2.png'],
            ],
            {'c1.png': B64_RED, 'c2.png': B64_BLUE},
        )
        parent = self.env['import.o2m'].search([('name', '=', 'O2M Parent')])
        self.assertEqual(len(parent), 1)
        self.assertEqual(len(parent.value), 2, 'both sub-records should exist')
        child1 = parent.value.filtered(lambda c: c.name == 'Child 1')
        child2 = parent.value.filtered(lambda c: c.name == 'Child 2')
        self.assertEqual(child1.image.content, PNG_RED, 'file of row 1 must land on the sub-record of row 1')
        self.assertEqual(child2.image.content, PNG_BLUE, 'file of row 2 must land on the sub-record of row 2')
        self.assertEqual(result['binary_filenames'], [
            {'model': 'import.o2m.child', 'id': child1.id, 'field': 'image', 'name': 'c1.png'},
            {'model': 'import.o2m.child', 'id': child2.id, 'field': 'image', 'name': 'c2.png'},
        ])

    def test_o2m_image_only_row(self):
        """A sub-record defined only by its image file must still be created."""
        result = self._import_with_files(
            'import.o2m',
            ['name', 'value/name', 'value/image'],
            [['O2M Parent', '', 'c1.png']],
            {'c1.png': B64_RED},
        )
        parent = self.env['import.o2m'].search([('name', '=', 'O2M Parent')])
        self.assertEqual(len(parent.value), 1, 'the image-only sub-record should exist')
        self.assertEqual(parent.value[0].image.content, PNG_RED)
        self.assertEqual(result['binary_filenames'][0]['model'], 'import.o2m.child')
        self.assertEqual(result['binary_filenames'][0]['id'], parent.value[0].id)

    def test_deeply_nested_o2m_image(self):
        """Images two o2m levels deep must reach the deepest sub-records."""
        result = self._import_with_files(
            'res.partner',
            ['name', 'child_ids/name', 'child_ids/child_ids/name', 'child_ids/child_ids/image_1920'],
            [
                ['Root Partner', 'Child Partner', 'Grandchild 1', 'g1.png'],
                ['', '', 'Grandchild 2', 'g2.png'],
            ],
            {'g1.png': B64_RED, 'g2.png': B64_BLUE},
        )
        root = self.env['res.partner'].search([('name', '=', 'Root Partner')])
        self.assertEqual(len(root), 1)
        self.assertEqual(len(root.child_ids), 1)
        grandchildren = root.child_ids.child_ids
        self.assertEqual(len(grandchildren), 2)
        self.assertEqual(
            sorted(g.image_1920.content for g in grandchildren),
            sorted([PNG_RED, PNG_BLUE]),
            'both files must land on the two grand-children',
        )
        self.assertEqual({entry['model'] for entry in result['binary_filenames']}, {'res.partner'})
        self.assertEqual({entry['field'] for entry in result['binary_filenames']}, {'image_1920'})
        self.assertEqual({entry['id'] for entry in result['binary_filenames']}, set(grandchildren.ids))

    def test_o2m_rows_then_top_level_image(self):
        """A record with o2m continuation rows followed by another record
        owning an image: file names are indexed by file row, the push must
        not be misaligned."""
        result = self._import_with_files(
            'res.partner',
            ['name', 'image_1920', 'child_ids/name'],
            [
                ['Partner A', 'a.png', 'Child 1'],
                ['', '', 'Child 2'],
                ['Partner B', 'b.png', ''],
            ],
            {'a.png': B64_RED, 'b.png': B64_BLUE},
        )
        partner_a = self.env['res.partner'].search([('name', '=', 'Partner A')])
        partner_b = self.env['res.partner'].search([('name', '=', 'Partner B')])
        self.assertEqual(len(partner_a.child_ids), 2)
        self.assertEqual(partner_a.image_1920.content, PNG_RED)
        self.assertEqual(partner_b.image_1920.content, PNG_BLUE, 'the image of the second record must not be lost')

    def test_update_existing_sub_records_by_database_id(self):
        """Updating existing sub-records referenced by ``/.id``: files must be
        pushed on those exact sub-records, not create new ones."""
        parent = self.env['import.o2m'].create({'name': 'Existing Parent'})
        child1, child2 = self.env['import.o2m.child'].create([
            {'name': 'Child 1', 'parent_id': parent.id},
            {'name': 'Child 2', 'parent_id': parent.id},
        ])
        self._import_with_files(
            'import.o2m',
            ['.id', 'value/.id', 'value/image'],
            [
                [parent.id, child1.id, 'c1.png'],
                ['', child2.id, 'c2.png'],
            ],
            {'c1.png': B64_RED, 'c2.png': B64_BLUE},
        )
        self.assertEqual(child1.image.content, PNG_RED)
        self.assertEqual(child2.image.content, PNG_BLUE)
        self.assertEqual(len(parent.value), 2, 'no extra sub-record should be created')

    def test_update_existing_sub_records_by_external_id(self):
        """Same as above, with the sub-records referenced by ``/id``."""
        parent = self.env['import.o2m'].create({'name': 'Existing Parent'})
        child = self.env['import.o2m.child'].create({'name': 'Child 1', 'parent_id': parent.id})
        self.env['ir.model.data'].create({
            'module': 'test_import_export',
            'name': 'existing_child',
            'model': 'import.o2m.child',
            'res_id': child.id,
        })
        self._import_with_files(
            'import.o2m',
            ['.id', 'value/id', 'value/image'],
            [
                [parent.id, 'test_import_export.existing_child', 'c1.png'],
            ],
            {'c1.png': B64_RED},
        )
        self.assertEqual(child.image.content, PNG_RED)
        self.assertEqual(len(parent.value), 1, 'no extra sub-record should be created')

    def test_uploaded_file_without_match_is_ignored(self):
        """A file name in the file that was not uploaded must not break anything."""
        result = self._execute_import(
            'import.o2m',
            ['name', 'value/name', 'value/image'],
            [['O2M Parent', 'Child 1', 'missing.png']],
        )
        self.assertEqual(len(result['binary_filenames']), 1)
        self._push_files(result, {})  # client uploaded nothing
        parent = self.env['import.o2m'].search([('name', '=', 'O2M Parent')])
        self.assertFalse(parent.value[0].image)

    def test_deep_o2m_chain_on_custom_models(self):
        """Replica of the extra-images scenario (product.template +
        product.image) on the test models, two o2m levels deep: files must
        land on the deepest sub-records."""
        result = self._import_with_files(
            'import.o2m',
            ['name', 'value/name', 'value/child_ids/name', 'value/child_ids/image'],
            [
                ['Deep Parent', 'Child A', 'Grand 1', 'g1.png'],
                ['', '', 'Grand 2', 'g2.png'],
            ],
            {'g1.png': B64_RED, 'g2.png': B64_BLUE},
        )
        parent = self.env['import.o2m'].search([('name', '=', 'Deep Parent')])
        self.assertEqual(len(parent), 1)
        self.assertEqual(len(parent.value), 1, 'the second row only continues the first child')
        grandchildren = parent.value[0].child_ids
        self.assertEqual(len(grandchildren), 2)
        self.assertEqual(
            sorted(g.image.content for g in grandchildren),
            sorted([PNG_RED, PNG_BLUE]),
            'both files must land on the two grand-children',
        )
        self.assertEqual({entry['model'] for entry in result['binary_filenames']}, {'import.o2m.grandchild'})
        self.assertEqual({entry['id'] for entry in result['binary_filenames']}, set(grandchildren.ids))

    def test_image_row_without_required_name_is_reported(self):
        """import.o2m.grandchild requires a name (like product.image): a row
        carrying only an image file must produce an explicit error message
        instead of a silent loss."""
        result = self._execute_import(
            'import.o2m',
            ['name', 'value/name', 'value/child_ids/name', 'value/child_ids/image'],
            [['Deep Parent', 'Child A', '', 'g1.png']],
        )
        self.assertTrue(result['messages'], 'the missing grand-child name should be reported')
        self.assertTrue(all(
            message['type'] == 'error' for message in result['messages']
        ))
        self.assertFalse(
            self.env['import.o2m.grandchild'].search([]),
            'the name-less grand-child should not be created',
        )

    def test_dryrun_returns_entries_without_creating(self):
        """The Test button (dry run) returns the entries but rolls everything back."""
        result = self._execute_import(
            'import.o2m',
            ['name', 'value/name', 'value/image'],
            [['O2M Parent', 'Child 1', 'c1.png']],
            dryrun=True,
        )
        self.assertEqual(len(result['binary_filenames']), 1)
        self.assertFalse(self.env['import.o2m'].search([('name', '=', 'O2M Parent')]))


class TestImportInlineImages(ImportImagesCommon):
    """Images imported inline (not uploaded in the import screen) must keep
    working through the regular phase-1 import."""

    def test_base64_inline_in_o2m(self):
        result = self._execute_import(
            'import.o2m',
            ['name', 'value/name', 'value/image'],
            [['O2M Parent', 'Child 1', B64_RED]],
        )
        self.assertNotIn('binary_filenames', result, 'inline images are imported in phase 1, nothing to push')
        parent = self.env['import.o2m'].search([('name', '=', 'O2M Parent')])
        self.assertEqual(parent.value[0].image.content, PNG_RED)

    def test_url_in_top_level_field(self):
        with patch(
            "odoo.addons.base_import.models.base_import.Base_ImportImport._import_file_by_url",
            return_value=PNG_RED,
        ):
            result = self._execute_import(
                'res.partner',
                ['name', 'image_1920'],
                [['Partner A', 'https://example.com/a.png']],
            )
        self.assertFalse(result.get('binary_filenames'), 'URL images are imported in phase 1, nothing to push')
        partner = self.env['res.partner'].search([('name', '=', 'Partner A')])
        self.assertEqual(partner.image_1920.content, PNG_RED)

    def test_url_in_o2m_field(self):
        with patch(
            "odoo.addons.base_import.models.base_import.Base_ImportImport._import_file_by_url",
            return_value=PNG_RED,
        ):
            result = self._execute_import(
                'import.o2m',
                ['name', 'value/name', 'value/image'],
                [['O2M Parent', 'Child 1', 'https://example.com/c1.png']],
            )
        self.assertFalse(result.get('binary_filenames'), 'URL images are imported in phase 1, nothing to push')
        parent = self.env['import.o2m'].search([('name', '=', 'O2M Parent')])
        self.assertEqual(parent.value[0].image.content, PNG_RED)
