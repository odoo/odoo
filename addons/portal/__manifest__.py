{
    "name": "Partner Portal",
    "version": "19.0.1.1",
    "category": "Hidden",
    "sequence": 9000,
    "summary": "Shared base for portal-user pages: templates, mixin, and controllers for external authenticated access",
    "description": """
Portal Framework
================

Base code for portal-authenticated pages: shared controller class, portal
mixin, and templates used by business addons to expose records to external
users (customers, vendors, signers, event attendees, mailing-list subscribers,
resellers, ...). The display label is "Customer Portal" for historical reasons,
but the technical scope covers any user with portal access rights.

The module deliberately does not depend on website-editing or theming
capabilities so portal pages can be rendered without the ``website`` module.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "http_routing",
        "auth_signup",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_templates.xml",
        "views/address_templates.xml",
        "views/mail_templates_public.xml",
        "views/portal_templates.xml",
        "views/res_config_settings_views.xml",
        "wizards/portal_share_views.xml",
        "wizards/portal_wizard_views.xml",
    ],
    "assets": {
        "web._assets_primary_variables": [
            "portal/static/src/scss/primary_variables.scss",
        ],
        "web._assets_frontend_helpers": [
            (
                "prepend",
                "portal/static/src/scss/bootstrap_overridden.scss",
            ),
        ],
        "web.assets_backend": [
            "portal/static/src/views/**/*",
        ],
        "web.assets_frontend": [
            "portal/static/src/interactions/**/*",
            "portal/static/src/scss/portal.scss",
            "portal/static/src/js/**/*",
            "portal/static/src/xml/**/*",
            "portal/static/src/signature_form/**/*",
            "portal/static/src/chatter/boot/boot_service.js",
        ],
        "web.assets_unit_tests_setup": [
            "portal/static/src/chatter/frontend/chatter_patch.js",
            "portal/static/src/chatter/boot/boot_service.js",
            "portal/static/src/chatter/frontend/portal_chatter.js",
            "portal/static/src/chatter/frontend/portal_chatter_service.js",
            "portal/static/src/interactions/**/*",
            "portal/static/src/js/components/input_confirmation_dialog/*",
            "portal/static/src/xml/**/*",
            "portal/static/src/signature_form/**/*",
        ],
        "web.assets_unit_tests": [
            "portal/static/tests/**/*.test.js",
        ],
        "web.assets_tests": [
            "portal/static/tests/tours/**/*",
        ],
        "portal.assets_chatter_helpers": [
            "web/static/src/views/view_dialogs/form_view_dialog.js",
            "web/static/src/views/view_dialogs/export_data_dialog.js",
            "web/static/src/webclient/debug/debug_menu.js",
            "web/static/src/webclient/debug/debug_menu_basic.js",
            "web/static/src/webclient/debug/debug_menu.xml",
            "web/static/src/webclient/debug/debug_menu.scss",
            "web/static/src/ui/commands/command_hook.js",
            "web/static/src/model/**/*",
            "web/static/src/search/**/*",
            "web/static/src/views/view.js",
            "web/static/src/views/ir/view_ir.js",
            "web/static/src/views/view_hook.js",
            "web/static/src/webclient/actions/action_dialog.js",
            "web/static/src/webclient/actions/reports/utils.js",
            "web/static/src/webclient/actions/reports/report_action.js",
            "web/static/src/webclient/actions/reports/report_hook.js",
            "web/static/src/views/view_utils.js",
            "web/static/src/core/field_types.js",
            "web/static/src/core/formatters.js",
            (
                "include",
                "mail.assets_core_common",
            ),
            (
                "include",
                "mail.assets_core_web_portal",
            ),
            (
                "include",
                "mail.assets_chatter_web_portal",
            ),
        ],
        "portal.assets_chatter": [
            (
                "include",
                "web._assets_helpers",
            ),
            (
                "include",
                "web._assets_frontend_helpers",
            ),
            "web/static/src/scss/pre_variables.scss",
            "web/static/lib/bootstrap/scss/_variables.scss",
            "web/static/lib/bootstrap/scss/_variables-dark.scss",
            "web/static/lib/bootstrap/scss/_maps.scss",
            "web/static/src/scss/tokens.scss",
            (
                "include",
                "html_editor._assets_editor",
            ),
            (
                "include",
                "portal.assets_chatter_helpers",
            ),
            "portal/static/src/chatter/core/**/*",
            "portal/static/src/chatter/frontend/**/*",
            (
                "remove",
                "mail/static/src/**/*.scss",
            ),
        ],
        "portal.assets_chatter_style": [
            (
                "include",
                "web._assets_helpers",
            ),
            (
                "include",
                "web._assets_backend_helpers",
            ),
            "web/static/src/scss/pre_variables.scss",
            "web/static/lib/bootstrap/scss/_variables.scss",
            "web/static/lib/bootstrap/scss/_variables-dark.scss",
            "web/static/lib/bootstrap/scss/_maps.scss",
            "portal/static/src/chatter/scss/primary_variables.scss",
            (
                "include",
                "web._assets_bootstrap_backend",
            ),
            "web/static/src/scss/tokens.scss",
            "web/static/src/scss/mimetypes.scss",
            "web/static/src/scss/ui.scss",
            "web/static/src/libs/fontawesome7/css/fontawesome.css",
            "web/static/src/libs/fontawesome7/css/solid.css",
            "web/static/src/libs/fontawesome7/css/regular.css",
            "web/static/src/libs/fontawesome7/css/brands.css",
            "web/static/lib/odoo_ui_icons/style.css",
            "web/static/src/webclient/webclient.scss",
            "web/static/src/core/avatar/avatar.scss",
            "web/static/src/components/dropdown/dropdown.scss",
            "web/static/src/components/emoji_picker/**/*",
            (
                "remove",
                "web/static/src/**/*.dark.scss",
            ),
            "mail/static/src/core/common/**/*.scss",
            "mail/static/src/chatter/web_portal/**/*.scss",
            "portal/static/src/chatter/scss/shadow.scss",
        ],
        "website.assets_inside_builder_iframe": [
            "portal/static/src/scss/portal.edit.*",
        ],
    },
    "esm": {
        "bundles": [
            "portal.assets_chatter",
        ],
        "dynamic_children": {
            "web.assets_frontend": [
                "portal.assets_chatter",
            ],
        },
    },
}
