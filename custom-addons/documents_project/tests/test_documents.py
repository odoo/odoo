# -*- coding: utf-8 -*-

import base64
from datetime import date, timedelta

from odoo import Command
from odoo.tests.common import users

from odoo.addons.project.tests.test_project_base import TestProjectCommon

GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
TEXT = base64.b64encode(bytes("workflow bridge project", 'utf-8'))


class TestCaseDocumentsBridgeProject(TestProjectCommon):

    def setUp(self):
        super(TestCaseDocumentsBridgeProject, self).setUp()
        self.folder_a = self.env['documents.folder'].create({
            'name': 'folder A',
        })
        self.folder_a_a = self.env['documents.folder'].create({
            'name': 'folder A - A',
            'parent_folder_id': self.folder_a.id,
        })
        self.attachment_txt = self.env['documents.document'].create({
            'datas': TEXT,
            'name': 'file.txt',
            'mimetype': 'text/plain',
            'folder_id': self.folder_a_a.id,
        })
        self.attachment_txt_2 = self.env['documents.document'].create({
            'datas': TEXT,
            'name': 'file2.txt',
            'mimetype': 'text/plain',
            'folder_id': self.folder_a_a.id,
        })
        self.workflow_rule_task = self.env['documents.workflow.rule'].create({
            'domain_folder_id': self.folder_a.id,
            'name': 'workflow rule create task on f_a',
            'create_model': 'project.task',
        })

        self.pro_admin = self.env['res.users'].create({
            'name': 'Project Admin',
            'login': 'proj_admin',
            'email': 'proj_admin@example.com',
            'groups_id': [(4, self.ref('project.group_project_manager'))],
        })

    def test_bridge_folder_workflow(self):
        """
        tests the create new business model (project).

        """
        self.assertEqual(self.attachment_txt.res_model, 'documents.document', "failed at default res model")
        self.workflow_rule_task.apply_actions([self.attachment_txt.id])

        self.assertEqual(self.attachment_txt.res_model, 'project.task', "failed at workflow_bridge_documents_project"
                                                                        " new res_model")
        task = self.env['project.task'].search([('id', '=', self.attachment_txt.res_id)])
        self.assertTrue(task.exists(), 'failed at workflow_bridge_documents_project task')
        self.assertEqual(self.attachment_txt.res_id, task.id, "failed at workflow_bridge_documents_project res_id")

    def test_bridge_parent_folder(self):
        """
        Tests the "Parent Workspace" setting
        """
        parent_folder = self.env.ref('documents_project.documents_project_folder')
        self.assertEqual(self.project_pigs.documents_folder_id.parent_folder_id, parent_folder, "The workspace of the project should be a child of the 'Projects' workspace.")

    def test_bridge_project_project_settings_on_write(self):
        """
        Makes sure the settings apply their values when an document is assigned a res_model, res_id
        """

        attachment_txt_test = self.env['ir.attachment'].create({
            'datas': TEXT,
            'name': 'fileText_test.txt',
            'mimetype': 'text/plain',
            'res_model': 'project.project',
            'res_id': self.project_pigs.id,
        })
        attachment_gif_test = self.env['ir.attachment'].create({
            'datas': GIF,
            'name': 'fileText_test.txt',
            'mimetype': 'text/plain',
            'res_model': 'project.task',
            'res_id': self.task_1.id,
        })

        txt_doc = self.env['documents.document'].search([('attachment_id', '=', attachment_txt_test.id)])
        gif_doc = self.env['documents.document'].search([('attachment_id', '=', attachment_gif_test.id)])

        self.assertEqual(txt_doc.folder_id, self.project_pigs.documents_folder_id, 'the text test document should have a folder')
        self.assertEqual(gif_doc.folder_id, self.project_pigs.documents_folder_id, 'the gif test document should have a folder')

    def test_bridge_document_is_shared(self):
        """
        Tests that the `is_shared` computed field on `documents.document` is working as intended.
        """
        self.assertFalse(self.attachment_txt.is_shared, "The document should not be shared by default")

        share_link = self.env['documents.share'].create({
            'folder_id': self.folder_a_a.id,
            'include_sub_folders': False,
            'type': 'domain',
        })
        self.folder_a_a._compute_is_shared()
        self.attachment_txt._compute_is_shared()

        self.assertTrue(self.attachment_txt.is_shared, "The document should be shared by a link sharing its folder")

        share_link.write({
            'folder_id': self.folder_a.id,
            'include_sub_folders': True,
        })
        self.folder_a_a._compute_is_shared()
        self.attachment_txt._compute_is_shared()

        self.assertTrue(self.attachment_txt.is_shared, "The document should be shared by a link sharing on of its ancestor folders with the subfolders option enabled")
        # We assume the rest of the cases depending on whether the document folder is shared are handled by the TestDocumentsFolder test in `documents`

        share_link.write({
            'include_sub_folders': False,
            'type': 'ids',
            'document_ids': [Command.link(self.attachment_txt.id)],
        })
        self.folder_a_a._compute_is_shared()
        self.attachment_txt._compute_is_shared()

        self.assertFalse(self.folder_a_a.is_shared, "The folder should not be shared")
        self.assertTrue(self.attachment_txt.is_shared, "The document should be shared by a link sharing it by id")

        share_link.write({'date_deadline': date.today() + timedelta(days=-1)})
        self.attachment_txt._compute_is_shared()

        self.assertFalse(self.attachment_txt.is_shared, "The document should be shared by an expired link sharing it by id")

        share_link.write({'date_deadline': date.today() + timedelta(days=1)})
        self.attachment_txt._compute_is_shared()

        self.assertTrue(self.attachment_txt.is_shared, "The document should be shared by a link sharing it by id and not expired yet")

    def test_copy_and_merge_folders(self):
        """
        Create 3 folders (folderA, folderB, folderC) with different properties (subfolders, tags, workflow actions)
        and merge them. The merged folder should have all the properties of the original folders combined.
        """
        folderA, folderB, folderC = self.env['documents.folder'].create([{
            'name': f'folder{l}',
        } for l in 'ABC'])

        folderA_child = self.env['documents.folder'].create({
            'name': 'folderA_child',
            'parent_folder_id': folderA.id,
        })
        folderB_facet = self.env['documents.facet'].create({
            'name': 'folderB_facet',
            'folder_id': folderB.id,
        })
        folderB_tag = self.env['documents.tag'].create({
            'name': 'folderB_tag',
            'facet_id': folderB_facet.id,
        })
        folderC_workflow_rule = self.env['documents.workflow.rule'].create({
            'name': 'folderC_workflow_rule',
            'domain_folder_id': folderC.id,
            'condition_type': 'criteria',
            'criteria_partner_id': self.partner_1.id,
        })
        self.env['documents.workflow.action'].create({
            'workflow_rule_id': folderC_workflow_rule.id,
            'action': 'remove',
        })

        copied_folder = (folderA + folderB + folderC)._copy_and_merge()

        self.assertEqual(len(copied_folder.children_folder_ids), 1)
        self.assertEqual(folderA_child.name, copied_folder.children_folder_ids[0].name)

        self.assertEqual(len(copied_folder.facet_ids), 1)
        facet_copy = copied_folder.facet_ids[0]
        self.assertEqual(folderB_facet.name, facet_copy.name)

        self.assertEqual(len(facet_copy.tag_ids), 1)
        self.assertEqual(folderB_tag.name, facet_copy.tag_ids[0].name)

        workflow_rule_copy_search = self.env['documents.workflow.rule'].search([('domain_folder_id', '=', copied_folder.id)])
        self.assertEqual(len(workflow_rule_copy_search), 1)
        workflow_rule_copy = workflow_rule_copy_search[0]
        self.assertEqual(folderC_workflow_rule.name, workflow_rule_copy.name)

        workflow_action_search = self.env['documents.workflow.action'].search([('workflow_rule_id', '=', workflow_rule_copy.id)])
        self.assertEqual(len(workflow_action_search), 1)

    def test_project_document_count(self):
        projects = self.project_pigs | self.project_goats
        self.assertEqual(self.project_pigs.document_count, 0)
        self.attachment_txt.write({
            'res_model': 'project.project',
            'res_id': self.project_pigs.id,
        })
        projects._compute_attached_document_count()
        self.assertEqual(self.project_pigs.document_count, 1, "The documents linked to the project should be taken into account.")
        self.env['documents.document'].create({
            'datas': GIF,
            'name': 'fileText_test.txt',
            'mimetype': 'text/plain',
            'folder_id': self.folder_a_a.id,
            'res_model': 'project.task',
            'res_id': self.task_1.id,
        })
        projects._compute_attached_document_count()
        self.assertEqual(self.project_pigs.document_count, 2, "The documents linked to the tasks of the project should be taken into account.")

    def test_project_document_search(self):
        # 1. Linking documents to projects/tasks
        documents_linked_to_task = self.env['documents.document'].search([('res_model', '=', 'project.task')])
        documents_linked_to_task_or_project = self.env['documents.document'].search([('res_model', '=', 'project.project')]) | documents_linked_to_task
        projects = self.project_pigs | self.project_goats
        self.assertEqual(projects[0].document_count, 0, "No project should have document linked to it initially")
        self.assertEqual(projects[1].document_count, 0, "No project should have document linked to it initially")
        self.attachment_txt.write({
            'res_model': 'project.project',
            'res_id': projects[0].id,
        })
        self.attachment_txt_2.write({
            'res_model': 'project.project',
            'res_id': projects[1].id,
        })
        doc_gif = self.env['documents.document'].create({
            'datas': GIF,
            'name': 'fileText_test.txt',
            'mimetype': 'text/plain',
            'folder_id': self.folder_a_a.id,
            'res_model': 'project.task',
            'res_id': self.task_1.id,
        })

        # 2. Project_id search tests
        # docs[0] --> projects[0] "Pigs"
        # docs[1] --> projects[1] "Goats"
        # docs[2] --> task "Pigs UserTask" --> projects[0] "Pigs"
        docs = self.attachment_txt + self.attachment_txt_2 + doc_gif
        # Needed for `inselect` leafs
        docs.flush_recordset()
        search_domains = [
            [('project_id', 'ilike', 'pig')],
            [('project_id', '=', 'pig')],
            [('project_id', '!=', 'Pigs')],
            [('project_id', '=', projects[0].id)],
            [('project_id', '!=', False)],
            [('project_id', '=', True)],
            [('project_id', '=', False)],
            [('project_id', 'in', projects.ids)],
            [('project_id', '!=', projects[0].id)],
            [('project_id', 'not in', projects.ids)],
            ['|', ('project_id', 'in', [projects[1].id]), ('project_id', '=', 'Pigs')],
        ]
        expected_results = [
            docs[0] + docs[2],
            self.env['documents.document'],
            docs[1] + documents_linked_to_task_or_project,
            docs[0] + docs[2],
            docs[0] + docs[1] + docs[2] + documents_linked_to_task_or_project,
            docs[0] + docs[1] + docs[2] + documents_linked_to_task_or_project,
            (self.env['documents.document'].search([]) - docs[0] - docs[1] - docs[2] - documents_linked_to_task_or_project),
            docs[0] + docs[1] + docs[2],
            docs[1] + documents_linked_to_task_or_project,
            documents_linked_to_task_or_project,
            docs[0] + docs[1] + docs[2],
        ]
        for domain, result in zip(search_domains, expected_results):
            self.assertEqual(self.env['documents.document'].search(domain), result, "The result of the search on the field project_id/task_id is incorrect (domain used: %s)" % domain)

        # 3. Task_id search tests
        task_2 = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Goats UserTask',
            'project_id': projects[1].id})

        self.attachment_txt.write({
            'res_model': 'project.task',
            'res_id': task_2,
        })
        # docs[0] --> tasks[1]  "Goats UserTask"
        # docs[2] --> tasks[0] "Pigs UserTask"
        tasks = self.task_1 | task_2
        self.env.flush_all()
        search_domains = [
            [('task_id', 'ilike', 'pig')],
            [('task_id', '=', 'pig')],
            [('task_id', '!=', 'Pigs UserTask')],
            [('task_id', '=', tasks[1].id)],
            [('task_id', '!=', False)],
            [('task_id', '=', False)],
            [('task_id', 'not in', tasks.ids)],
            ['&', ('task_id', 'in', tasks.ids), '!', ('task_id', 'ilike', 'goats')],
        ]
        expected_results = [
            docs[2],
            self.env['documents.document'],
            docs[0] + documents_linked_to_task,
            docs[0],
            docs[0] + docs[2] + documents_linked_to_task,
            (self.env['documents.document'].search([]) - docs[0] - docs[2] - documents_linked_to_task),
            documents_linked_to_task,
            docs[2],
        ]
        for domain, result in zip(search_domains, expected_results):
            self.assertEqual(self.env['documents.document'].search(domain), result, "The result of the search on the field project_id/task_id is incorrect (domain used: %s)" % domain)

    def test_project_folder_creation(self):
        project = self.env['project.project'].create({
            'name': 'Project',
            'use_documents': False,
        })
        self.assertFalse(project.documents_folder_id, "A project created with the documents feature disabled should have no workspace")
        project.use_documents = True
        self.assertTrue(project.documents_folder_id, "A workspace should be created for the project when enabling the documents feature")

        documents_folder = project.documents_folder_id
        project.use_documents = False
        self.assertTrue(project.documents_folder_id, "The project should keep its workspace when disabling the feature")
        project.use_documents = True
        self.assertEqual(documents_folder, project.documents_folder_id, "No workspace should be created when enablind the documents feature if the project already has a workspace")

    def test_project_task_access_document(self):
        """
        Tests that 'MissingRecord' error should not be rasied when trying to switch
        workspace for a non-existing document.

        - The 'active_id' here is the 'id' of a non-existing document.
        - We then try to access 'All' workspace by calling the 'search_panel_select_range'
            method. We should be able to access the workspace.
        """
        missing_id = self.env['documents.document'].search([], order='id DESC', limit=1).id + 1
        result = self.env['documents.document'].with_context(
            active_id=missing_id, active_model='project.task',
            limit_folders_to_project=True).search_panel_select_range('folder_id')
        self.assertTrue(result)

    def test_copy_project(self):
        """
        When duplicating a project, there should be exactly one copy of the folder linked to the project.
        If there is the `no_create_folder` context key, then the folder should not be copied (note that in normal flows,
        when this context key is used, it is expected that a folder will be copied/created manually, so that we don't
        end up with a project having the documents feature enabled but no folder).
        """
        last_folder_id = self.env['documents.folder'].search([], order='id desc', limit=1).id
        self.project_pigs.copy()
        self.assertEqual(len(self.env['documents.folder'].search([('id', '>', last_folder_id)])), 1, "There should only be one new folder created.")
        self.project_goats.with_context(no_create_folder=True).copy()
        self.assertEqual(len(self.env['documents.folder'].search([('id', '>', last_folder_id + 1)])), 0, "There should be no new folder created.")

    @users('proj_admin')
    def test_rename_project(self):
        """
        When renaming a project, the corresponding folder should be renamed as well.
        Even when the user does not have write access on the folder, the project should be able to rename it.
        """
        new_name = 'New Name'
        self.project_pigs.with_user(self.env.user).name = new_name
        self.assertEqual(self.project_pigs.documents_folder_id.name, new_name, "The folder should have been renamed along with the project.")
