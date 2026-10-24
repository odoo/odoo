{
    "name": "SIFNEXT Asset",
    "version": "19.0.1.0.0",
    "category": "Operations",
    "summary": "Asset Management",
    "depends": ["base", "mail", "sif_keuangan"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/asset_category_views.xml",
        "views/asset_depreciation_views.xml",
        "views/asset_views.xml",
    ],
    "installable": True,
    "application": True,
}