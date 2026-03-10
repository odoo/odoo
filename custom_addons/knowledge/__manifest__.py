# -*- coding: utf-8 -*-
{
    "name": "Knowledge",
    "version": "19.0.1.0.0",
    "category": "Knowledge",
    "summary": "Community compatibility wrapper for the standard Odoo Knowledge app.",
    "description": "This module provides a compatibility bridge so dependencies on technical module 'knowledge' work with the community knowledge stack.",
    "author": "Kodoo",
    "license": "LGPL-3",
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
    "data": [
        "views/knowledge_branding.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
