import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_user_group_settings", {
    url: "/odoo/settings?debug=assets,tests",
    steps: () => [
        {
            trigger: 'button[data-menu-xmlid="base.menu_users"]',
            content: "open user menu",
            run: "click",
        },
        {
            trigger: 'a[data-menu-xmlid="base.menu_action_res_users"]',
            content: "open users & companies menu",
            run: "click",
        },
        {
            trigger: '.o_data_row:first-child .o_field_cell[name="name"]',
            content: "open users menu",
            run: "click",
        },

        {
            trigger: 'a.nav-link[name="technical_access_rights"]',
            content: "show Technical Access Rights",
            run: "click",
        },
        {
            trigger: 'a.nav-link[name="technical_access_rights"].active',
        },
        {
            trigger: '.o_notebook_content:not(.o_data_cell(:contains("Settings"))',
            content: "check if demo user does not have 'Settings' access",
        },
        {
            trigger: 'a.nav-link[name="access_rights"]',
            content: "show Access Rights",
            run: "click",
        },
        {
            trigger: 'a.nav-link[name="access_rights"].active',
        },
        {
            trigger:
                '.o_field_widget[name="group_ids"] .o_inner_group:has(label:contains("Administration")) select.o_input',
            content: "Add 'Access Rights' access to demo user",
            run: `select 2`,
        },
        {
            trigger: 'a.nav-link[name="technical_access_rights"]',
            content: "show changes in Technical Access Rights",
            run: "click",
        },
        {
            trigger: 'a.nav-link[name="technical_access_rights"].active',
        },
        {
            trigger: '.o_notebook_content .o_data_cell:contains("Access Rights")',
            content: "check if demo user have 'Settings' with 'Access Rights' level",
        },

        {
            trigger: 'button[data-menu-xmlid="base.menu_users"]',
            content: "open user menu and auto save",
            run: "click",
        },
        {
            trigger: 'a[data-menu-xmlid="base.menu_action_res_users"]',
            content: "open users & companies menu",
            run: "click",
        },
        {
            trigger: ".o_action_manager > .o_list_view",
            content: "wait for the Users list view to be displayed",
        },
        {
            trigger: '.o_data_row:first-child .o_field_cell[name="name"]',
            content: "open users menu",
            run: "click",
        },
        {
            trigger:
                '.o_notebook_content select.o_input:has(option:contains("Access Rights"):selected)',
            content: "check if demo user have 'Settings' with 'Access Rights' level",
        },
        {
            trigger: 'a.nav-link[name="technical_access_rights"]',
            content: "show Technical Access Rights",
            run: "click",
        },
        {
            trigger: 'a.nav-link[name="technical_access_rights"].active',
        },
        {
            trigger: '.o_notebook_content .o_data_cell:contains("Access Rights")',
            content: "check if demo user have 'Settings' with 'Access Rights' level",
        },
    ],
});
