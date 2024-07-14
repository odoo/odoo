# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import datetime
import json

from freezegun import freeze_time
from psycopg2 import IntegrityError

from .common import SpreadsheetTestCommon, TEST_CONTENT, GIF
from odoo.exceptions import AccessError
from odoo.tools import mute_logger
from odoo.tests import Form
from odoo.tests.common import new_test_user


class SpreadsheetDocuments(SpreadsheetTestCommon):
    @classmethod
    def setUpClass(cls):
        super(SpreadsheetDocuments, cls).setUpClass()
        cls.folder = cls.env["documents.folder"].create({"name": "Test folder"})

    def test_action_open_new_spreadsheet(self):
        action = self.env["documents.document"].action_open_new_spreadsheet()
        spreadsheet_id = action["params"]["spreadsheet_id"]
        document = self.env["documents.document"].browse(spreadsheet_id)
        self.assertTrue(document.exists())
        self.assertEqual(document.handler, "spreadsheet")
        self.assertEqual(document.mimetype, "application/o-spreadsheet")
        self.assertEqual(document.name, "Untitled spreadsheet")
        self.assertEqual(document.datas, document._empty_spreadsheet_data_base64())
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "action_open_spreadsheet")
        self.assertTrue(action["params"]["is_new_spreadsheet"])


    def test_action_open_new_spreadsheet_with_locale(self):
        self.env["res.lang"].create(
            {
                "code": "en_FR",
                "name": "Custom Locale",
                "thousands_sep": " ",
                "decimal_point": ",",
                "date_format": "%d-%m-%Y",
                "time_format": "%H %M %S",
                "active": True,
            }
        )
        user = self.env['res.users'].create({
            "name": "Custom user",
            "login": "custom_user",
            "lang": "en_FR"
        })

        action = self.env["documents.document"].with_user(user).action_open_new_spreadsheet()
        spreadsheet_id = action["params"]["spreadsheet_id"]
        document = self.env["documents.document"].browse(spreadsheet_id)
        self.assertTrue(document.exists())

        data = document.join_spreadsheet_session()["data"]
        expected_locale = {
            "code": "en_FR",
            "name": "Custom Locale",
            "thousandsSeparator": " ",
            "decimalSeparator": ",",
            "dateFormat": "dd-mm-yyyy",
            "timeFormat": "hh mm ss",
            "formulaArgSeparator": ";",
        }
        self.assertEqual(data["settings"]["locale"], expected_locale)

    def test_action_open_new_spreadsheet_in_folder(self):
        action = self.env["documents.document"].action_open_new_spreadsheet({
            "folder_id": self.folder.id
        })
        spreadsheet_id = action["params"]["spreadsheet_id"]
        document = self.env["documents.document"].browse(spreadsheet_id)
        self.assertEqual(document.folder_id, self.folder)

    def archive_existing_spreadsheet(self):
        """Existing spreadsheet in the database can influence some test results"""
        self.env["documents.document"].search([("handler", "=", "spreadsheet")]).active = False

    def test_spreadsheet_default_folder(self):
        document = self.env["documents.document"].create({
            "spreadsheet_data": r"{}",
            "handler": "spreadsheet",
            "mimetype": "application/o-spreadsheet",
        })
        self.assertEqual(
            document.folder_id,
            self.env.company.documents_spreadsheet_folder_id,
            "It should have been assigned the default Spreadsheet Folder"
        )
        self.env.company.documents_spreadsheet_folder_id = self.env['documents.folder'].create({
            'name': 'Spreadsheet - Test Folder',
        })
        document = self.env["documents.document"].create({
            "spreadsheet_data": r"{}",
            "handler": "spreadsheet",
            "mimetype": "application/o-spreadsheet",
        })
        self.assertEqual(
            document.folder_id,
            self.env.company.documents_spreadsheet_folder_id,
            "It should have been assigned the default Spreadsheet Folder"
        )

    def test_normal_doc_default_folder(self):
        """Default spreadsheet folder is not assigned to normal documents"""
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self.env["documents.document"].create({
                "spreadsheet_data": r"{}",
                "mimetype": "application/o-spreadsheet",
            })

    def test_spreadsheet_no_default_folder(self):
        """Folder is not overwritten by the default spreadsheet folder"""
        document = self.env["documents.document"].create({
            "spreadsheet_data": r"{}",
            "folder_id": self.folder.id,
            "handler": "spreadsheet",
            "mimetype": "application/o-spreadsheet",
        })
        self.assertEqual(document.folder_id, self.folder, "It should be in the specified folder")

    def test_spreadsheet_to_display_with_domain(self):
        self.archive_existing_spreadsheet()

        with freeze_time("2020-02-03"):
            spreadsheet1 = self.create_spreadsheet(name="My Spreadsheet")
        with freeze_time("2020-02-02"):
            spreadsheet2 = self.create_spreadsheet(name="Untitled Spreadsheet")
        spreadsheets = self.env["documents.document"].get_spreadsheets_to_display([("name", "ilike", "My")])
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet1.id])
        spreadsheets = self.env["documents.document"].get_spreadsheets_to_display([("name", "ilike", "Untitled")])
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet2.id])
        spreadsheets = self.env["documents.document"].get_spreadsheets_to_display([("name", "ilike", "Spreadsheet")])
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet1.id, spreadsheet2.id])

    def test_spreadsheet_to_display_with_offset_limit(self):
        self.archive_existing_spreadsheet()
        user = new_test_user(
            self.env, login="Jean", groups="documents.group_documents_user"
        )
        with freeze_time("2020-02-02"):
            spreadsheet1 = self.create_spreadsheet(user=user, name="My Spreadsheet 1")
        with freeze_time("2020-02-03"):
            spreadsheet2 = self.create_spreadsheet(user=user, name="My Spreadsheet 2")
        with freeze_time("2020-02-04"):
            spreadsheet3 = self.create_spreadsheet(name="My Spreadsheet 3")
        with freeze_time("2020-02-05"):
            spreadsheet4 = self.create_spreadsheet(user=user, name="SP 4")
        with freeze_time("2020-02-06"):
            spreadsheet5 = self.create_spreadsheet(name="SP 5")
        with freeze_time("2020-02-07"):
            spreadsheet6 = self.create_spreadsheet(name="SP 6")

        #########
        # ADMIN #
        #########

        # Only the last opened spreadsheet.
        spreadsheets = self.env["documents.document"].get_spreadsheets_to_display([], offset=0, limit=1)
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet6.id])

        # Two last opened spreadsheets.
        spreadsheets = self.env["documents.document"].get_spreadsheets_to_display([], offset=0, limit=2)
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet6.id, spreadsheet5.id])

        # Ordered first by last opened, and then by id.
        spreadsheets = self.env["documents.document"].get_spreadsheets_to_display([], offset=2, limit=2)
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet3.id, spreadsheet4.id])

        # Ordered first by last opened, and then by id without limit.
        spreadsheets = self.env["documents.document"].get_spreadsheets_to_display([], offset=2)
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet3.id, spreadsheet4.id, spreadsheet2.id, spreadsheet1.id])

        # Ordered first by last opened, and then by id without limit with a domain.
        spreadsheets = self.env["documents.document"].get_spreadsheets_to_display([("name", "ilike", "My Spreadsheet")])
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet3.id, spreadsheet2.id, spreadsheet1.id])

        # Ordered first by last opened, and then by id without limit with a domain.
        spreadsheets = self.env["documents.document"].get_spreadsheets_to_display([("name", "ilike", "SP ")])
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet6.id, spreadsheet5.id, spreadsheet4.id])

        ########
        # JEAN #
        ########

        # Only the last opened spreadsheet.
        spreadsheets = self.env["documents.document"].with_user(user).get_spreadsheets_to_display([], offset=0, limit=1)
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet4.id])

        # Two last opened spreadsheets.
        spreadsheets = self.env["documents.document"].with_user(user).get_spreadsheets_to_display([], offset=0, limit=2)
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet4.id, spreadsheet2.id])

        # Ordered first by last opened, and then by id.
        spreadsheets = self.env["documents.document"].with_user(user).get_spreadsheets_to_display([], offset=2, limit=2)
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet1.id, spreadsheet6.id])

        # Ordered first by last opened, and then by id without limit.
        spreadsheets = self.env["documents.document"].with_user(user).get_spreadsheets_to_display([], offset=2)
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet1.id, spreadsheet6.id, spreadsheet5.id, spreadsheet3.id])

        # Ordered first by last opened, and then by id without limit with a domain.
        spreadsheets = self.env["documents.document"].with_user(user).get_spreadsheets_to_display([("name", "ilike", "My Spreadsheet")])
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet2.id, spreadsheet1.id, spreadsheet3.id])

        # Ordered first by last opened, and then by id without limit with a domain.
        spreadsheets = self.env["documents.document"].with_user(user).get_spreadsheets_to_display([("name", "ilike", "SP ")])
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet4.id, spreadsheet6.id, spreadsheet5.id])

    def test_spreadsheet_to_display(self):
        self.archive_existing_spreadsheet()
        document = self.create_spreadsheet()
        archived_document = self.env["documents.document"].create(
            {
                "spreadsheet_data": r"{}",
                "folder_id": self.folder.id,
                "active": False,
                "handler": "spreadsheet",
                "mimetype": "application/o-spreadsheet",
            }
        )
        spreadsheets = self.env["documents.document"].get_spreadsheets_to_display([])
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertTrue(
            document.id in spreadsheet_ids, "It should contain the new document"
        )
        self.assertFalse(
            archived_document.id in spreadsheet_ids,
            "It should not contain the archived document",
        )

    def test_spreadsheet_to_display_create_order(self):
        self.archive_existing_spreadsheet()
        with freeze_time("2020-02-02 18:00"):
            spreadsheet1 = self.create_spreadsheet()
        with freeze_time("2020-02-15 18:00"):
            spreadsheet2 = self.create_spreadsheet()
        spreadsheets = self.env["documents.document"].get_spreadsheets_to_display([])
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet2.id, spreadsheet1.id])

    def test_spreadsheet_to_display_write_order(self):
        self.archive_existing_spreadsheet()
        with freeze_time("2020-02-02 18:00"):
            spreadsheet1 = self.create_spreadsheet()
        with freeze_time("2020-02-15 18:00"):
            spreadsheet2 = self.create_spreadsheet()
        spreadsheet1.spreadsheet_data = "data"
        spreadsheets = self.env["documents.document"].get_spreadsheets_to_display([])
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet1.id, spreadsheet2.id])

    def test_spreadsheet_to_display_join_session(self):
        self.archive_existing_spreadsheet()
        with freeze_time("2020-02-02 18:00"):
            spreadsheet1 = self.create_spreadsheet()
        with freeze_time("2020-02-15 18:00"):
            spreadsheet2 = self.create_spreadsheet()
        spreadsheet1.join_spreadsheet_session()
        spreadsheets = self.env["documents.document"].get_spreadsheets_to_display([])
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet1.id, spreadsheet2.id])

    def test_spreadsheet_to_display_without_contrib(self):
        self.archive_existing_spreadsheet()
        user = new_test_user(
            self.env, login="Jean", groups="documents.group_documents_user"
        )
        with freeze_time("2020-02-02 18:00"):
            spreadsheet1 = self.create_spreadsheet(user=user)
        with freeze_time("2020-02-15 18:00"):
            spreadsheet2 = self.create_spreadsheet()
        spreadsheets = (
            self.env["documents.document"].with_user(user).get_spreadsheets_to_display([])
        )
        spreadsheet_ids = [s["id"] for s in spreadsheets]
        self.assertEqual(spreadsheet_ids, [spreadsheet1.id, spreadsheet2.id])

    def test_spreadsheet_to_display_access_portal(self):
        portal = new_test_user(self.env, "Test user", groups="base.group_portal")
        with self.assertRaises(
            AccessError, msg="A portal user should not be able to read spreadsheet"
        ):
            self.env["documents.document"].with_user(
                portal
            ).get_spreadsheets_to_display([])

    def test_spreadsheet_to_display_access_ir_rule(self):
        user = new_test_user(
            self.env, "Test user", groups="documents.group_documents_manager"
        )

        model = self.env.ref("documents.model_documents_document")
        group = self.env.ref("documents.group_documents_manager")

        manager_doc = self.create_spreadsheet(user=user)
        visible_doc = self.create_spreadsheet(user=user)
        # archive existing record rules which might allow access (disjunction between record rules)
        record_rules = self.env["ir.rule"].search(
            [
                ("model_id", "=", model.id),
            ]
        )
        record_rules.active = False
        self.env["ir.rule"].create(
            {
                "name": "test record rule",
                "model_id": model.id,
                "groups": [(4, group.id)],
                "domain_force": f"[('id', '=', {visible_doc.id})]",  # always rejects
            }
        )

        spreadsheets = (
            self.env["documents.document"].with_user(user).get_spreadsheets_to_display([])
        )
        self.assertEqual(
            [s["id"] for s in spreadsheets], [visible_doc.id], "filtering issue"
        )

        with self.assertRaises(AccessError, msg="record rule should have raised"):
            manager_doc.with_user(user).spreadsheet_data = "{}"

    def test_spreadsheet_to_display_access_field_groups(self):
        existing_groups = self.env["documents.document"]._fields["name"].groups
        self.env["documents.document"]._fields["name"].groups = "base.group_system"
        user = new_test_user(
            self.env, "Test user", groups="documents.group_documents_manager"
        )

        with self.assertRaises(AccessError, msg="field should be protected"):
            self.env["documents.document"].with_user(user).get_spreadsheets_to_display([])
        self.env["documents.document"]._fields["name"].groups = existing_groups

    def test_save_template(self):
        context = {
            "default_spreadshee_name": "Spreadsheet test",
            "default_template_name": "Spreadsheet test - Template",
            "default_spreadsheet_data": TEST_CONTENT,
            "default_thumbnail": GIF,
        }
        wizard = Form(
            self.env["save.spreadsheet.template"].with_context(context)
        ).save()
        wizard.save_template()
        template = self.env["spreadsheet.template"].search(
            [["name", "=", "Spreadsheet test - Template"]]
        )
        self.assertTrue(template, "It should have created a template")
        self.assertEqual(template.name, "Spreadsheet test - Template")
        self.assertEqual(template.spreadsheet_data, TEST_CONTENT)
        self.assertEqual(template.thumbnail, GIF)

    def test_user_right_own_template(self):
        user = new_test_user(
            self.env, "Test user", groups="documents.group_documents_user"
        )
        template = (
            self.env["spreadsheet.template"]
            .with_user(user)
            .create(
                {
                    "name": "hello",
                    "spreadsheet_data": TEST_CONTENT,
                }
            )
        )
        template.write(
            {
                "name": "bye",
            }
        )
        template.unlink()

    def test_user_right_not_own_template(self):
        manager = new_test_user(
            self.env, "Test manager", groups="documents.group_documents_manager"
        )
        user = new_test_user(
            self.env, "Test user", groups="documents.group_documents_user"
        )
        template = (
            self.env["spreadsheet.template"]
            .with_user(manager)
            .create(
                {
                    "name": "hello",
                    "spreadsheet_data": TEST_CONTENT,
                }
            )
        )
        with self.assertRaises(
            AccessError, msg="cannot write on template of your friend"
        ):
            template.with_user(user).write(
                {
                    "name": "bye",
                }
            )
        with self.assertRaises(
            AccessError, msg="cannot delete template of your friend"
        ):
            template.with_user(user).unlink()
        template.name = "bye"
        template.unlink()

    def test_contributor_write_spreadsheet_data(self):
        document = self.create_spreadsheet()
        user = new_test_user(
            self.env, "Test Manager", groups="documents.group_documents_manager"
        )
        document.with_user(user).write({"spreadsheet_data": r"{}"})
        contributor = self.env["spreadsheet.contributor"].search(
            [("user_id", "=", user.id), ("document_id", "=", document.id)]
        )
        self.assertEqual(len(contributor), 1, "The contribution should be registered")

    def test_contributor_move_workspace(self):
        document = self.create_spreadsheet()
        new_folder = self.env["documents.folder"].create({"name": "New folder"})
        user = new_test_user(
            self.env, "Test Manager", groups="documents.group_documents_manager"
        )
        document.with_user(user).write({"folder_id": new_folder.id})
        contributor = self.env["spreadsheet.contributor"].search(
            [("user_id", "=", user.id), ("document_id", "=", document.id)]
        )
        self.assertEqual(
            len(contributor), 0, "The contribution should not be registered"
        )

    def test_document_replacement_with_handler(self):
        document = self.env["documents.document"].create({
            "spreadsheet_data": r"{}",
            "folder_id": self.folder.id,
            "handler": "spreadsheet",
            "mimetype": "application/o-spreadsheet",
        })
        vals = {
            "name": "file",
            "folder_id": self.folder.id,
            "spreadsheet_data": r"{}",
            "handler": "spreadsheet"
        }
        document.write(vals)
        self.assertEqual(document.handler, "spreadsheet", "The handler must contain the value of the handler mentioned in vals")

    def test_document_replacement_data_only(self):
        document = self.env["documents.document"].create({
            "name": "file",
            "spreadsheet_data": r"{}",
            "folder_id": self.folder.id,
            "handler": "spreadsheet",
        })
        vals = {
            "spreadsheet_data": r"{}",
        }
        document.write(vals)
        self.assertEqual(document.handler, "spreadsheet", "The handler should not have changed")

    def test_document_replacement_with_other_mimetype(self):

        document = self.env["documents.document"].create({
            "spreadsheet_data": r"{}",
            "folder_id": self.folder.id,
            "handler": "spreadsheet",
            "mimetype": "application/o-spreadsheet",
        })
        vals = {
            "name": "test.txt",
            "datas": b'aGVsbG8hCg==\n',
            "folder_id": self.folder.id,
            "mimetype": "text/plain",
        }
        document.write(vals)
        self.assertEqual(document.handler, False, "The handler should have been reset")

    def test_document_replacement_with_spreadsheet_mimetype(self):
        document = self.env["documents.document"].create({
            "raw": b'some text',
            "folder_id": self.folder.id,
            "mimetype": "text/plain",
        })
        vals = {
            "spreadsheet_data": r"{}",
            "mimetype": "application/o-spreadsheet",
        }
        document.write(vals)
        self.assertEqual(document.handler, False, "the file should not be recognized as a spreadsheet")

    def test_document_replacement_with_handler_and_other_mimetype(self):
        document = self.env["documents.document"].create({
            "spreadsheet_data": r"{}",
            "folder_id": self.folder.id,
            "handler": "spreadsheet",
            "mimetype": "application/o-spreadsheet",
        })
        vals = {
            "name": "spreadsheet_file",
            "folder_id": self.folder.id,
            "spreadsheet_data": r"{}",
            "mimetype": "application/json",
            "handler": "spreadsheet"
        }
        document.write(vals)
        self.assertEqual(document.handler, "spreadsheet", "the handler must contain the value of the handler mentioned in vals")

    def test_create_document_with_spreadsheet_mimetype(self):
        document = self.env["documents.document"].create({
            "spreadsheet_data": r"{}",
            "folder_id": self.folder.id,
            "mimetype": "application/o-spreadsheet",
        })
        self.assertEqual(document.handler, False, "the file should not be recognized as a spreadsheet")

    def test_read_spreadsheet_data(self):
        document = self.env["documents.document"].create({
            "name": "test.txt",
            "datas": base64.encodebytes(b'{ "sheets": [] }'),
            "handler": "spreadsheet",
            "mimetype": "application/o-spreadsheet",
            "folder_id": self.folder.id,
        })
        self.assertEqual(document.spreadsheet_data, '{ "sheets": [] }')

    def test_read_spreadsheet_data_bin_size_ctx(self):
        document = self.env["documents.document"].with_context(bin_size=True).create({
            "name": "test.txt",
            "datas": base64.encodebytes(b"{}"),
            "handler": "spreadsheet",
            "mimetype": "application/o-spreadsheet",
            "folder_id": self.folder.id,
        })
        self.assertEqual(document.spreadsheet_data, "{}")

    def test_read_non_spreadsheet_data(self):
        document = self.env["documents.document"].create({
            "name": "test.txt",
            "datas": TEST_CONTENT,
            "mimetype": "text/plain",
            "folder_id": self.folder.id,
        })
        self.assertEqual(document.spreadsheet_data, False)

    def test_write_spreadsheet_data(self):
        document = self.env["documents.document"].create({
            "name": "test.txt",
            "datas": base64.encodebytes(b"{}"),
            "handler": "spreadsheet",
            "mimetype": "application/o-spreadsheet",
            "folder_id": self.folder.id,
        })
        data = b"{ sheets: [] }"
        document.spreadsheet_data = data
        self.assertEqual(document.datas, base64.b64encode(data))

    def test_copy_spreadsheet_revisions(self):
        spreadsheet = self.create_spreadsheet()
        user = new_test_user(
            self.env, login="Jean", groups="documents.group_documents_user"
        )
        spreadsheet.dispatch_spreadsheet_message(self.new_revision_data(spreadsheet))

        #########
        # ADMIN #
        #########
        copy_admin = spreadsheet.copy()
        self.assertEqual(
            len(copy_admin.spreadsheet_revision_ids),
            1,
            "The revision should be copied with admin access right",
        )

        ########
        # NON-ADMIN #
        ########
        spreadsheet.invalidate_recordset()
        copy_non_admin = spreadsheet.with_user(user).copy()
        self.assertEqual(
            len(copy_non_admin.spreadsheet_revision_ids),
            1,
            "The revision should be copied with non-admin access right",
        )

    def test_copy_spreadsheet_snapshot(self):
        spreadsheet = self.create_spreadsheet()
        spreadsheet.dispatch_spreadsheet_message(self.new_revision_data(spreadsheet))
        self.snapshot(
            spreadsheet,
            spreadsheet.server_revision_id, "snapshot-revision-id", {"sheets": [], "revisionId": "snapshot-revision-id"},
        )
        copy = spreadsheet.copy()
        self.assertEqual(
            copy.spreadsheet_snapshot,
            spreadsheet.spreadsheet_snapshot,
            "Copy should have the same snapshot data",
        )

    def test_autovacuum_remove_old_empty_spreadsheet(self):
        self.env["documents.document"].search([('handler', '=', 'spreadsheet')]).unlink()

        self.create_spreadsheet(name="Spreadsheet", values={
            "create_date": datetime(2023, 5, 15, 18)
        })
        self.assertEqual(len(self.env["documents.document"].search([('handler', '=', 'spreadsheet')])), 1)

        with freeze_time("2023-05-16 19:00"):
            self.env["documents.document"]._gc_spreadsheet()
        self.assertEqual(len(self.env["documents.document"].search([('handler', '=', 'spreadsheet')])), 0)

    def test_autovacuum_keep_new_empty_spreadsheet(self):
        self.env["documents.document"].search([('handler', '=', 'spreadsheet')]).unlink()

        self.create_spreadsheet(name="Spreadsheet", values={
            "create_date": datetime(2023, 5, 16, 18)
        })
        self.assertEqual(len(self.env["documents.document"].search([('handler', '=', 'spreadsheet')])), 1)

        with freeze_time("2023-05-16 19:00"):
            self.env["documents.document"]._gc_spreadsheet()
        self.assertEqual(len(self.env["documents.document"].search([('handler', '=', 'spreadsheet')])), 1)

    def test_autovacuum_keep_old_spreadsheet_with_revision(self):
        self.env["documents.document"].search([('handler', '=', 'spreadsheet')]).unlink()

        spreadsheet = self.create_spreadsheet(name="Spreadsheet", values={
            "create_date": datetime(2023, 5, 15, 18)
        })
        commands = self.new_revision_data(spreadsheet)
        spreadsheet.dispatch_spreadsheet_message(commands)

        self.assertEqual(len(self.env["documents.document"].search([('handler', '=', 'spreadsheet')])), 1)

        with freeze_time("2023-05-16 19:00"):
            self.env["documents.document"]._gc_spreadsheet()
        self.assertEqual(len(self.env["documents.document"].search([('handler', '=', 'spreadsheet')])), 1)

    def test_join_session_name_is_a_string(self):
        spreadsheet = self.create_spreadsheet(name="")
        self.assertEqual(spreadsheet.name, "")
        self.assertEqual(spreadsheet.display_name, False)
        session_data = spreadsheet.join_spreadsheet_session()
        self.assertEqual(session_data["name"], "")

    def test_copy_image_in_snapshot(self):
        spreadsheet = self.create_spreadsheet()
        image = self.env["ir.attachment"].create({
            "name": "image.png",
            "datas": b"test",
            "res_model": "documents.document",
            "res_id": spreadsheet.id,
        })
        spreadsheet_data = {
            "revisionId": "NEW_REVISION",
            "sheets": [{
                "figures": [
                    {
                        "id": "14",
                        "x": 0,
                        "y": 0,
                        "width": 10,
                        "height": 10,
                        "tag": "image",
                        "data": {
                            "path": f"/web/image/{image.id}",
                            "size": {"width": 10, "height": 10},
                            "mimetype": "image/png"
                        }
                    }
                ],
            }],
        }
        spreadsheet.spreadsheet_data = json.dumps(spreadsheet_data)
        self.snapshot(spreadsheet, "START_REVISION", "NEW_REVISION", spreadsheet_data)
        copy = spreadsheet.copy({
            "spreadsheet_data": spreadsheet.spreadsheet_data,
            "spreadsheet_snapshot": spreadsheet.spreadsheet_snapshot,
        })
        copied_data = json.loads(copy.spreadsheet_data)
        copied_snapshot = copy._get_spreadsheet_snapshot()
        for data_copy in (copied_data, copied_snapshot):
            image_definition = data_copy["sheets"][0]["figures"][0]["data"]
            path = image_definition["path"]
            attachment_copy_id = int(path.split("/")[3])
            attachment_copy = self.env["ir.attachment"].browse(attachment_copy_id)
            self.assertNotEqual(attachment_copy_id, image.id)
            self.assertEqual(attachment_copy.res_id, copy.id)
            self.assertEqual(attachment_copy.res_model, "documents.document")
            self.assertEqual(image_definition["path"], f"/web/image/{attachment_copy_id}")

    def test_copy_image_in_revision(self):
        spreadsheet = self.create_spreadsheet()
        image = self.env["ir.attachment"].create({
            "name": "image.png",
            "datas": b"test",
            "res_model": "documents.document",
            "res_id": spreadsheet.id,
        })
        commands = [{
            "type": "CREATE_IMAGE",
            "figureId": "image-id",
            "position": {"x": 0, "y": 0},
            "size": {"width": 1, "height": 1},
            "definition": {
                "path": "/web/image/%s" % image.id,
            }
        }]

        spreadsheet.dispatch_spreadsheet_message(self.new_revision_data(spreadsheet, commands=commands))
        copy = spreadsheet.copy()
        revision = copy.spreadsheet_revision_ids
        command = json.loads(revision.commands)["commands"][0]
        path = command["definition"]["path"]
        attachment_copy_id = int(path.split("/")[3])
        attachment_copy = self.env["ir.attachment"].browse(attachment_copy_id)
        self.assertNotEqual(attachment_copy_id, image.id)
        self.assertEqual(attachment_copy.res_id, copy.id)
        self.assertEqual(attachment_copy.res_model, "documents.document")
        self.assertEqual(command["definition"]["path"], f"/web/image/{attachment_copy_id}")

    def test_create_spreadsheet_with_image_linked_to_other_record(self):
        image = self.env["ir.attachment"].create({
            "name": "image.png",
            "datas": b"test",
            "res_model": self.env.user._name,
            "res_id": self.env.user.id,
        })
        spreadsheet_data = {
            "sheets": [{
                "figures": [
                    {
                        "id": "14",
                        "x": 0,
                        "y": 0,
                        "width": 10,
                        "height": 10,
                        "tag": "image",
                        "data": {
                            "path": f"/web/image/{image.id}",
                            "size": {"width": 10, "height": 10},
                            "mimetype": "image/png"
                        }
                    }
                ],
            }],
        }
        spreadsheet = self.create_spreadsheet({
            "spreadsheet_data": json.dumps(spreadsheet_data)
        })
        copy = spreadsheet.copy({
            "spreadsheet_data": spreadsheet.spreadsheet_data,
            "spreadsheet_snapshot": spreadsheet.spreadsheet_snapshot,
        })
        image_definition = json.loads(copy.spreadsheet_data)["sheets"][0]["figures"][0]["data"]
        path = image_definition["path"]
        attachment_copy_id = int(path.split("/")[3])
        attachment_copy = self.env["ir.attachment"].browse(attachment_copy_id)
        self.assertNotEqual(attachment_copy_id, image.id)
        self.assertEqual(attachment_copy.res_id, copy.id)
        self.assertEqual(attachment_copy.res_model, "documents.document")
        self.assertEqual(image_definition["path"], f"/web/image/{attachment_copy_id}")

    def test_delete_spreadsheet_delete_image(self):
        spreadsheet = self.create_spreadsheet()
        image = self.env["ir.attachment"].create({
            "name": "image.png",
            "datas": b"test",
            "res_model": "documents.document",
            "res_id": spreadsheet.id,
        })
        self.assertTrue(image)
        spreadsheet.unlink()
        self.assertFalse(image.exists())
