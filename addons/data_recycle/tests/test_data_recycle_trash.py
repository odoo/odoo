# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestDataRecycleTrash(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.TrashRecord = cls.env['data_recycle.trash.record']
        cls.TrashModel = cls.env['data_recycle.trash.model']

    def _track(self, model='res.partner.category', **kwargs):
        return self.TrashModel.create({
            'res_model_id': self.env['ir.model']._get(model).id,
            **kwargs,
        })

    def test_never_tracked_model_not_configurable(self):
        """ Models excluded by _get_never_tracked cannot be configured: their
        tracking would be silently ignored."""
        for model in ('data_recycle.trash.record', 'data_recycle.record', 'mail.followers'):
            with self.assertRaises(ValidationError, msg=model):
                self._track(model)

    def test_untracked_model_not_captured(self):
        """ Deleting a record of a non-configured model creates no trash."""
        category = self.env['res.partner.category'].create({'name': 'Untracked'})
        category.unlink()
        self.assertFalse(self.TrashRecord.search([('res_model_name', '=', 'res.partner.category')]))

    def test_tracked_model_captured(self):
        """ Deleting a tracked record snapshots it into data_recycle.trash.record."""
        self._track()
        category = self.env['res.partner.category'].create({'name': 'Tracked', 'color': 3})
        cat_id = category.id
        category.unlink()

        trash = self.TrashRecord.search([
            ('res_model_name', '=', 'res.partner.category'),
            ('record_id', '=', str(cat_id)),
        ])
        self.assertEqual(len(trash), 1)
        self.assertEqual(trash.deleted_by, self.env.user)
        self.assertEqual(trash.record_name, 'Tracked')
        self.assertEqual(trash.field_data['name'], 'Tracked')
        self.assertEqual(trash.field_data['color'], 3)

    def test_domain_restricts_capture(self):
        """ Only deleted records matching the configured filter are captured."""
        self._track(domain="[('color', '=', 1)]")
        matching = self.env['res.partner.category'].create({'name': 'Match', 'color': 1})
        other = self.env['res.partner.category'].create({'name': 'NoMatch', 'color': 2})
        (matching | other).unlink()

        trash = self.TrashRecord.search([('res_model_name', '=', 'res.partner.category')])
        self.assertEqual(len(trash), 1)
        self.assertEqual(trash.record_name, 'Match')

    def test_capture_with_restricted_fields(self):
        """ Capturing a model with group-restricted fields (e.g. res.users)
        must not raise AccessError for a non-superuser."""
        self._track('res.users')
        user = self.env['res.users'].create({'name': 'Trash Test', 'login': 'trash_test'})
        user_id = user.id
        user.with_user(self.env.ref('base.user_admin')).unlink()

        trash = self.TrashRecord.search([
            ('res_model_name', '=', 'res.users'),
            ('record_id', '=', str(user_id)),
        ])
        self.assertEqual(len(trash), 1)
        self.assertEqual(trash.field_data['login'], 'trash_test')

    def test_excluded_field_not_snapshotted(self):
        """ Excluded fields are not stored in the snapshot."""
        color_field = self.env['ir.model.fields']._get('res.partner.category', 'color')
        self._track(excluded_field_ids=[(6, 0, color_field.ids)])
        category = self.env['res.partner.category'].create({'name': 'Foo', 'color': 5})
        category.unlink()

        trash = self.TrashRecord.search([('res_model_name', '=', 'res.partner.category')], limit=1)
        self.assertIn('name', trash.field_data)
        self.assertNotIn('color', trash.field_data)

    def test_inactive_trash_model_not_captured(self):
        """ An archived configuration stops capturing."""
        trash_model = self._track()
        trash_model.active = False
        category = self.env['res.partner.category'].create({'name': 'Baz'})
        category.unlink()
        self.assertFalse(self.TrashRecord.search([('res_model_name', '=', 'res.partner.category')]))

    def test_restore_record(self):
        """ Restoring recreates the record from the snapshot and removes the
        trash entry."""
        self._track()
        category = self.env['res.partner.category'].create({'name': 'Restorable', 'color': 7})
        category.unlink()
        trash = self.TrashRecord.search([('res_model_name', '=', 'res.partner.category')], limit=1)

        trash.action_restore()

        restored = self.env['res.partner.category'].search([('name', '=', 'Restorable')])
        self.assertEqual(len(restored), 1)
        self.assertEqual(restored.color, 7)
        self.assertFalse(trash.exists())

    def test_restore_skips_dangling_many2one(self):
        """ A many2one pointing to a record deleted in the meantime is not
        restored, but the rest of the snapshot is."""
        self._track()
        parent = self.env['res.partner.category'].create({'name': 'Parent'})
        child = self.env['res.partner.category'].create({'name': 'Child', 'parent_id': parent.id})
        child_id = child.id
        (child | parent).unlink()

        trash = self.TrashRecord.search([
            ('res_model_name', '=', 'res.partner.category'),
            ('record_id', '=', str(child_id)),
        ])
        trash.action_restore()

        restored = self.env['res.partner.category'].search([('name', '=', 'Child')])
        self.assertEqual(len(restored), 1)
        self.assertFalse(restored.parent_id)

    def test_gc_respects_retention(self):
        """ The autovacuum removes entries older than the per-model retention only."""
        self._track(retention_days=30)
        category = self.env['res.partner.category'].create({'name': 'Old'})
        category.unlink()
        trash = self.TrashRecord.search([('res_model_name', '=', 'res.partner.category')], limit=1)

        # Recent entry: kept.
        self.TrashRecord._gc_trash_records()
        self.assertTrue(trash.exists())

        # Aged beyond retention: removed. Trash records are frozen, so age
        # the entry with a direct SQL update.
        self.env.cr.execute(
            "UPDATE data_recycle_trash_record SET delete_date = %s WHERE id = %s",
            (fields.Datetime.now() - timedelta(days=31), trash.id))
        trash.invalidate_recordset(['delete_date'])
        self.TrashRecord._gc_trash_records()
        self.assertFalse(trash.exists())

    def test_trash_record_frozen_but_purgeable(self):
        """ A trash record cannot be modified once created, even as sudo, but
        system admins can permanently delete it (empty the trash)."""
        self._track()
        category = self.env['res.partner.category'].create({'name': 'Frozen'})
        category.unlink()
        trash = self.TrashRecord.search([('res_model_name', '=', 'res.partner.category')], limit=1)

        with self.assertRaises(UserError):
            trash.sudo().write({'record_name': 'Tampered'})

        trash.with_user(self.env.ref('base.user_admin')).unlink()
        self.assertFalse(trash.exists())
