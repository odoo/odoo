{
    "name": "Assets - Documents",
    "version": "1.0",
    "category": "Productivity/Documents",
    "summary": "File an asset's documents in the folder its kind keeps",
    "description": """
An asset's documents are filed by the kind of thing it is: each kind names, per company, the
folder its documents land in, the tags they carry, and whether they are centralised at all.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "document",
        "resource_asset",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_actions_server_data.xml",
        "views/resource_asset_kind_views.xml",
        "views/resource_asset_views.xml",
    ],
    "auto_install": True,
    "post_init_hook": "_document_resource_asset_post_init",
}
