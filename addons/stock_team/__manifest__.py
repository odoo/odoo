{
    "name": "Inventory Teams",
    "version": "1.0",
    "category": "Supply Chain/Inventory",
    "summary": "Operators work in teams: operation types belong to a team, and so do their transfers",
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "stock",
        "team",
    ],
    "data": [
        "security/stock_team_security.xml",
        "security/ir.model.access.csv",
        "views/team_team_views.xml",
        "views/stock_picking_views.xml",
        "views/stock_team_menus.xml",
    ],
    "auto_install": True,
}
