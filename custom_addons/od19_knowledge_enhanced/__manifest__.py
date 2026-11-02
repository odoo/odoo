{
    "name": "Knowledge Enhanced",
    "version": "19.0.2.0.0",
    "category": "Knowledge",
    "summary": "Smart knowledge base with full-text search and templates",
    "author": "OD19",
    "license": "LGPL-3",
    "depends": ["base", "mail", "document_page", "document_knowledge", "od19_internal_issue"],
    "data": [
        "data/knowledge_article_data.xml",
        "views/knowledge_article_views.xml",
        "views/knowledge_article_templates.xml",
    ],
    "installable": True,
    "application": False,
    "icon": "/od19_knowledge_enhanced/static/description/icon.svg",
}
