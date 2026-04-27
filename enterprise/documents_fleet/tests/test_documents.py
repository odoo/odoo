# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user
from odoo.tests.common import tagged, TransactionCase

TEXT = base64.b64encode(bytes("documents_fleet", 'utf-8'))


@tagged('post_install', '-at_install', 'test_document_bridge')
class TestCaseDocumentsBridgeFleet(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fleet_folder = cls.env.ref('documents_fleet.document_fleet_folder')
        company = cls.env.user.company_id
        company.documents_fleet_settings = True
        company.documents_fleet_folder = cls.fleet_folder
        cls.manager_1 = new_test_user(cls.env, "test fleet manager",
            groups="documents.group_documents_user, fleet.fleet_group_manager"
        )
        cls.manager_2 = new_test_user(cls.env, "test fleet manager 2",
            groups="fleet.fleet_group_manager"
        )
        cls.user = new_test_user(cls.env, "user")
        # Create the Audi vehicle
        brand = cls.env["fleet.vehicle.model.brand"].create({
            "name": "Audi",
        })
        model = cls.env["fleet.vehicle.model"].create({
            "brand_id": brand.id,
            "name": "A3",
        })
        cls.fleet_vehicle = cls.env["fleet.vehicle"].create({
            "model_id": model.id,
            "driver_id": cls.manager_1.partner_id.id,
            "plan_to_change_car": False
        })

    def test_fleet_attachment(self):
        """
        Make sure the vehicle attachment is linked to the documents application

        Test Case:
        =========
            - Attach attachment to Audi vehicle
            - Check if the document is created
            - Check the res_id of the document
            - Check the res_model of the document
        """
        self.fleet_folder.access_ids.unlink()
        self.env['documents.access'].create([
            {'document_id': self.fleet_folder.id, 'partner_id': self.manager_1.partner_id.id, 'role': 'edit'},
            {'document_id': self.fleet_folder.id, 'partner_id': self.manager_2.partner_id.id, 'role': 'edit'},
        ])
        attachment_txt_test = self.env['ir.attachment'].with_user(self.manager_1).create({
            'datas': TEXT,
            'name': 'fileText_test.txt',
            'mimetype': 'text/plain',
            'res_model': 'fleet.vehicle',
            'res_id': self.fleet_vehicle.id,
        })
        document = self.env['documents.document'].search([('attachment_id', '=', attachment_txt_test.id)])
        self.assertTrue(document.exists(), "It should have created a document")
        self.assertEqual(document.res_id, self.fleet_vehicle.id, "fleet record linked to the document ")
        self.assertEqual(document.owner_id, self.manager_1, "default document owner is the current user")
        self.assertEqual(document.res_model, self.fleet_vehicle._name, "fleet model linked to the document")
        self.assertTrue(document.is_access_via_link_hidden)
        self.assertEqual(document.access_internal, 'none')
        self.assertEqual(document.access_via_link, 'none')
        access = document.access_ids
        self.assertEqual(len(access), 2, "The access should have been propagated")

        document.with_user(self.manager_2).name

        with self.assertRaises(AccessError):
            document.with_user(self.user).name

    def test_disable_fleet_centralize_option(self):
        """
        Make sure that the document is not created when your Fleet Centralize is disabled.

        Test Case:
        =========
            - Disable the option Centralize your Fleet' documents option
            - Add an attachment to a fleet vehicle
            - Check whether the document is created or not
        """
        company = self.env.user.company_id
        company.documents_fleet_settings = False

        attachment_txt_test = self.env['ir.attachment'].create({
            'datas': TEXT,
            'name': 'fileText_test.txt',
            'mimetype': 'text/plain',
            'res_model': 'fleet.vehicle',
            'res_id': self.fleet_vehicle.id,
        })
        document = self.env['documents.document'].search([('attachment_id', '=', attachment_txt_test.id)])
        self.assertFalse(document.exists(), 'the document should not exist')

    def test_company_reset_documents_folder_id(self):
        """Check the update of folder_id when the bridge is enabled/disabled on a company

        Note that this test is named after the method implemented in the document module
        because there is no company field pointing to a folder in documents itself."""
        new_company = self.env['res.company'].create({'name': 'New Company'})
        self.assertEqual(new_company.documents_fleet_folder, self.fleet_folder)
        test_companies = self.env.company + new_company
        # Only our two test companies should use this folder
        self.env['res.company'].sudo().search([('id', 'not in', test_companies.ids)]).documents_fleet_folder = False

        fleet_folder_2 = self.env['documents.document'].create({'name': 'Fleet Folder 2', 'type': 'folder'})

        self.env.company.documents_fleet_settings = False
        self.assertEqual(test_companies.with_context(allowed_company_ids=test_companies.ids).documents_fleet_folder,
                         self.fleet_folder,
                         "Both companies should still be linked to Fleet Folder")

        with self.assertRaises(UserError):
            self.fleet_folder.action_archive()
        with self.assertRaises(UserError):
            self.fleet_folder.unlink()

        new_company.documents_fleet_folder = fleet_folder_2
        self.fleet_folder.action_archive()

        new_company.documents_fleet_settings = False
        self.assertEqual(new_company.documents_fleet_folder,
                         fleet_folder_2,
                         "The folder should still be linked with disabled bridge")

        new_company.documents_fleet_settings = True
        self.assertEqual(new_company.documents_fleet_folder, fleet_folder_2)
        new_company.documents_fleet_settings = False
        fleet_folder_2.unlink()
        new_company.documents_fleet_settings = True
        self.assertFalse(new_company.documents_fleet_folder, 'There should be no value as the default is archived')
        new_company.documents_fleet_settings = False
        self.fleet_folder.action_unarchive()
        new_company.documents_fleet_settings = True
        self.assertEqual(new_company.documents_fleet_folder,
                         self.fleet_folder,
                         "The default folder should have been re-used")

    def test_link_document_when_no_vehicle_exists(self):
        """
        Ensure that a document cannot be linked when no vehicles exist.

        Test Case:
        =========
            - Archive all vehicles to ensure no vehicle exists.
            - create a document in the fleet folder
            - Try to link the document.
            - Check that a UserError is raised
            - If a vehicle exists, it should be used as `default_resource_ref`.
        """
        self.env['fleet.vehicle'].search([]).write({
            'active': False
        })
        self.assertFalse(self.env['fleet.vehicle'].search([]), "There should be no active vehicles.")
        attachment = self.env['ir.attachment'].create({
            'name': "An Email without attachment",
            'type': 'binary',
            'raw':  '<p>A mail body</p>',
            'mimetype': 'application/documents-email',
            'res_model': 'documents.document',
        })
        document = self.env['documents.document'].create({
            'name': "An Email with attachment",
            'folder_id': self.fleet_folder.id,
            'attachment_id': attachment.id,
        })
        with self.assertRaises(UserError):
            document.action_link_to_record("fleet.vehicle")

        vehicle = self.env["fleet.vehicle"].create({
            "model_id": self.fleet_vehicle.model_id.id,
        })
        res = document.action_link_to_record("fleet.vehicle")
        context = res.get('context', {})
        self.assertEqual(context.get('default_resource_ref'), f"fleet.vehicle,{vehicle.id}")
