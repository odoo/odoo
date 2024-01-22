# © 2013-2015 Therp BV (<http://therp.nl>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
{
    "name": "Window actions for client side paging",
    "summary": (
        "Allows a developer to trigger a pager to show the previous "
        "or next next record in the form view"
    ),
    "author": "Hunki Enterprises BV, Therp BV,Odoo Community Association (OCA)",
    "version": "16.0.1.0.0",
    "category": "Technical",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "web_ir_actions_act_window_page/static/src/web_ir_actions_act_window_page.esm.js",
        ]
    },
    "demo": ["demo/demo_action.xml"],
    "installable": True,
    "license": "AGPL-3",
    "website": "https://github.com/OCA/web",
}
