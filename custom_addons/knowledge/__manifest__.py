# -*- coding: utf-8 -*-
{
    "name": "Knowledge (Community Wrapper)",
    "version": "19.0.1.0.0",
    "category": "Knowledge",
    "summary": "Wrapper module that installs all OCA knowledge modules to emulate the Enterprise version.",
    "description": "This module acts as a bridge so other apps requesting 'knowledge' receive the OCA alternatives.",
    "author": "Anderson Clayton",
    "depends": [
        "attachment_preview",
        "attachment_zipped_download",
        "document_knowledge",
        "document_page",
        "document_page_access_group",
        "document_page_approval",
        "document_page_group",
        "document_page_partner",
        "document_page_project",
        "document_page_reference",
        "document_page_tag",
        "document_url"
    ],
    "data": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
