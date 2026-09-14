{
    "name": "Purchase Teams",
    "version": "1.0",
    "category": "Supply Chain/Purchase",
    "summary": "Buyers work in teams: team documents, team access and team reporting in Purchase",
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "purchase",
        "team",
    ],
    "data": [
        "security/purchase_team_security.xml",
        "security/ir.model.access.csv",
        "views/team_team_views.xml",
        "views/purchase_order_views.xml",
        "views/purchase_team_menus.xml",
    ],
    "auto_install": True,
}
