{
    "name": "Teams",
    "version": "1.0",
    "category": "Hidden",
    "summary": "Teams shared by sales, purchase, inventory, manufacturing, maintenance, helpdesk and quality",
    "description": """
One team model for every application that organises people in teams. A team
carries its members, leader and company once; each application flags the
teams it uses, adds its own settings and email alias, and points its
documents at the team directly.
""",
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "mail",
    ],
    "data": [
        "security/team_security.xml",
        "security/ir.model.access.csv",
        "views/team_views.xml",
        "views/team_member_views.xml",
        "views/team_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "team/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "team/static/tests/**/*",
        ],
    },
    "pre_init_hook": "pre_init_hook",
}
