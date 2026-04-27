{
    "name": """Uruguay - E-Remitos""",
    "countries": ["uy"],
    "category": "Accounting/Localizations/EDI",
    "version": "1.0",
    "description": """Enhances stock picking operations with compliant electronic delivery guides (e-Remitos) for Uruguay. This module integrates with the EDI system to generate e-Remitos according to Uruguayan fiscal requirements.""",
    "author": "ADHOC SA",
    "depends": [
        "l10n_uy_edi",
        "stock_account",
        "sale_stock",
    ],
    "data": [
        "data/l10n_latam.document.type.csv",
        "views/cfe_template.xml",
        "views/stock_picking_views.xml",
    ],
    "installable": True,
    'license': 'OEEL-1',
}
