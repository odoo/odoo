{
    "name": "Knowledge",
    "version": "19.0.1.0.0",
    "summary": "Centralize and manage your knowledge base - Kore Tier 2 substitute for knowledge",
    "category": "Productivity/Knowledge",
    "author": "Kore",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "web",
    ],
    "data": [
        "security/knowledge_groups.xml",
        "security/knowledge_rules.xml",
        "security/ir.model.access.csv",
        "data/knowledge_article_data.xml",
        "views/knowledge_article_views.xml",
        "views/knowledge_article_member_views.xml",
        "views/knowledge_menus.xml",
    ],
    "installable": True,
    "application": True,
}

