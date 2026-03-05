# Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Documents Knowledge",
    "version": "19.0.1.0.2",
    "author": "OpenERP SA,"
    "MONK Software, "
    "Tecnativa, "
    "ForgeFlow, "
    "Odoo Community Association (OCA)",
    "category": "Knowledge",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/knowledge",
    "depends": ["base"],
    "data": [
        "data/ir_module_category.xml",
        "security/document_knowledge_security.xml",
        "data/res_users.xml",
        "views/document_knowledge.xml",
        "views/res_config.xml",
    ],
    "demo": ["demo/document_knowledge.xml"],
    "installable": True,
    "application": True,
}

