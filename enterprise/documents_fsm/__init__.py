# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def _documents_fsm_post_init(env):
    fsm_projects = env["project.project"].search([("is_fsm", "=", True), ("use_documents", "=", True)])

    # Search for folders that are descendants of fsm_projects folders and have documents
    subfolders_with_documents = env["documents.document"].search([
        ("id", "child_of", fsm_projects.documents_folder_id.ids),
        ("type", '=', "folder"),
        ("shortcut_document_id", "=", False),
        ("children_ids", "any", ["|", ("type", "!=", "folder"), ("shortcut_document_id", "!=", False)]),
    ])

    folders_with_non_empty_subfolders = {
        folder.id
        for folder in fsm_projects.documents_folder_id
        if any(
            subfolder.parent_path.startswith(folder.parent_path)
            for subfolder in subfolders_with_documents
        )
    }

    for project in fsm_projects:
        if project.document_count == 0:
            project.use_documents = False

            project_folder = project.documents_folder_id
            if (
                project_folder.document_count == 0
                and project_folder.id not in folders_with_non_empty_subfolders
            ):
                project.documents_folder_id.unlink()
            else:
                project.documents_folder_id = False
