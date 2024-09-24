from odoo.tests.common import TransactionCase


class TestAudit(TransactionCase):

    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()
        cls.audittestb1 = cls.env['test.auditb'].create({'name': 'auditb1'})
        cls.audittestb2 = cls.env['test.auditb'].create({'name': 'auditb2'})
        cls.audittestb3 = cls.env['test.auditb'].create({'name': 'audit3'})
        cls.audittestb4 = cls.env['test.auditb'].create({'name': 'audit4'})
        cls.audittestb5 = cls.env['test.auditb'].create({'name': 'audit5'})

        cls.audittest = cls.env['test.audit'].create({'name': 'audit1'})
        cls.audittest_filtered = cls.env['test.audit'].create({'name': 'audit_filter', 'bool1': True})
        cls.audittest2 = cls.env['test.audit'].create({'name': "audit2", 'field2': "Hello", 'auditb_id': cls.audittestb2.id})
        return res

    def test_is_auditable_field_with_val(self):
        # Name is neither in no_audit or no_val
        self.assertTrue(self.audittest._is_auditable_field_with_val('name'))
        # field1 in _audit_no_val_fieldnames
        self.assertFalse(self.audittest._is_auditable_field_with_val('field1'))
        # field2 in _no_audit_fieldnames
        self.assertFalse(self.audittest._is_auditable_field_with_val('field2'))
        # no_audit and no_val should also override hardcoded set
        self.assertTrue(self.audittestb2._is_auditable_field_with_val('name'))
        self.assertFalse(self.audittestb2._is_auditable_field_with_val('field1'))
        self.assertFalse(self.audittestb2._is_auditable_field_with_val('field2'))
        self.assertFalse(self.audittestb2._is_auditable_field_with_val('bool1'))
        # Ensure ORM fields aren't taken into account
        self.assertFalse(self.audittestb2._is_auditable_field_with_val('write_uid'))

    def test_filter_audit_records(self):
        # Filter remove bool1 == False
        filtered = self.env['test.audit'].search([])._filter_audit_records()
        self.assertIn(self.audittest, filtered)
        self.assertNotIn(self.audittest_filtered, filtered)

    def test_save_values_for_log(self):
        saved_value = self.audittest._save_values_for_log({'name': 'audit1', 'field1': 'foo'})
        self.assertEqual({self.audittest.id: {'name': 'audit1'}}, saved_value)
        # Record filtered
        self.assertEqual({}, self.audittest_filtered._save_values_for_log({'name': 'useless'}))
        # no_audit_fieldnames
        self.assertEqual({}, self.audittest2._save_values_for_log({'field2': 'useless'}))
        # Save recordset
        save_multi = self.env['test.audit'].search([])._save_values_for_log({'name': 'audit1'})
        self.assertEqual({self.audittest.id: {'name': 'audit1'},
            self.audittest2.id: {'name': 'audit2'}}, save_multi)
        # No MissingError in order to be consistent with write
        company = self.env['res.company'].browse(9999)
        company._save_values_for_log({'name': "FakeCompany"})
        # Unknown field
        with self.assertRaises(ValueError):
            self.audittest._save_values_for_log({'name': 'audit1', 'field_doesnt_exist': 'foo'})

    def test_format_log(self):
        audittest = self.audittest
        audittest2 = self.env['test.audit'].create({'name': 'audit2', 'auditb_id': self.audittestb2.id,
            'auditb_ids': [self.audittestb3.id, self.audittestb4.id]})
        # No saved_values
        self.assertEqual("name: 'audit1'", audittest._format_log('name'))
        # Default value or empty recordset not logged
        self.assertEqual("", audittest._format_log('auditb_id'))
        self.assertEqual("", audittest._format_log('field1'))
        # Boolean default value is audited
        self.assertEqual("bool1: False", audittest._format_log('bool1'))
        self.assertEqual(f"auditb_id: {self.audittestb2}", self.audittest2._format_log('auditb_id'))
        # With saved_values
        saved_values = audittest._save_values_for_log({'name'})
        # Before and Current is the same so log nothing
        self.assertEqual("", audittest._format_log('name', saved_values[audittest.id]))
        audittest.name = "audit1_new"
        self.assertEqual("name: 'audit1' ==> 'audit1_new'", audittest._format_log('name',
            saved_values[audittest.id]))
        # Remove 1 from recordset
        saved_values = audittest2._save_values_for_log({'auditb_ids'})
        audittest2.auditb_ids = [self.audittestb3.id]
        self.assertEqual(f"auditb_ids: Removed: {self.audittestb4} ", audittest2._format_log('auditb_ids',
            saved_values[audittest2.id]))
        # Add 1 to recordset
        saved_values = audittest2._save_values_for_log({'auditb_ids'})
        audittest2.auditb_ids = [self.audittestb3.id, self.audittestb4.id]
        self.assertEqual(f"auditb_ids: Added: {self.audittestb4}", audittest2._format_log('auditb_ids',
            saved_values[audittest2.id]))
        # Remove multiple from recordset
        saved_values = audittest2._save_values_for_log({'auditb_ids'})
        audittest2.auditb_ids = None
        self.assertEqual(f"auditb_ids: Removed: {self.audittestb3 | self.audittestb4} ", audittest2._format_log('auditb_ids',
            saved_values[audittest2.id]))
        # Add multiple to recordset
        saved_values = audittest2._save_values_for_log({'auditb_ids'})
        audittest2.auditb_ids = [self.audittestb3.id, self.audittestb4.id]
        self.assertEqual(f"auditb_ids: Added: {self.audittestb3 | self.audittestb4}", audittest2._format_log('auditb_ids',
            saved_values[audittest2.id]))
        # Add & Remove to recordset
        saved_values = audittest2._save_values_for_log({'auditb_ids'})
        audittest2.auditb_ids = [self.audittestb3.id, self.audittestb5.id]
        self.assertEqual(f"auditb_ids: Removed: {self.audittestb4} Added: {self.audittestb5}",
            audittest2._format_log('auditb_ids', saved_values[audittest2.id]))
        # Add single record
        saved_values = audittest._save_values_for_log({'auditb_ids'})
        audittest.auditb_ids = [self.audittestb3.id]
        self.assertEqual(f"auditb_ids: {self.env['test.auditb']} ==> {self.audittestb3}",
            audittest._format_log('auditb_ids', saved_values[audittest.id]))
        # Remove from single record
        saved_values = audittest._save_values_for_log({'auditb_ids'})
        audittest.auditb_ids = None
        self.assertEqual(f"auditb_ids: {self.audittestb3} ==> {self.env['test.auditb']}",
            audittest._format_log('auditb_ids', saved_values[audittest.id]))

    def test_log_audit_changes(self):
        create_vals = {'name': 'audit1', 'bool2': True, 'auditb_id': self.audittestb2.id}
        audittest = self.env['test.audit'].create(create_vals)
        saved_values = {audittest.id: {'name': 'foo', 'bool2': False, 'auditb_id': self.audittestb1}}
        audittest._log_audit_changes(create_vals, "suffix", saved_values)
        with self.assertLogs() as audit_log:
            audittest._log_audit_changes(create_vals, "suffix", saved_values)
        expected_log_value = f"{audittest} with \"name: 'foo' ==> 'audit1', bool2: True, auditb_id: {self.audittestb1} ==> {self.audittestb2}\" by {self.env.user}"
        self.assertEqual(expected_log_value, audit_log.records[0].getMessage())

    def test_create_write(self):
        create_vals = {'name': 'audit1', 'bool2': True, 'auditb_id': self.audittestb2.id}
        with self.assertLogs() as audit_log:
            audittest = self.env['test.audit'].create(create_vals)
            audittest.name = "foo"
        self.assertEqual('audit.test.audit.create', audit_log.records[0].name)
        expected_log_value = f"{audittest} with \"name: 'audit1', bool2: True, auditb_id: {self.audittestb2}\" by {self.env.user}"
        self.assertEqual(expected_log_value, audit_log.records[0].getMessage())
        self.assertEqual('audit.test.audit.write', audit_log.records[1].name)
        expected_log_value = f"{audittest} with \"name: 'audit1' ==> 'foo'\" by {self.env.user}"
        self.assertEqual(expected_log_value, audit_log.records[1].getMessage())
        with self.assertNoLogs():
            self.audittest_filtered.name = "Test"
