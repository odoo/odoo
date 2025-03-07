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
            content: "show Technical Administrator",
            run: "click",
        },
        {
            trigger: '.o_notebook_content:not(.o_data_cell(:contains("Administrator"))',
            content: "check if demo user does not have 'Administrator' access",
        },
        {
            trigger: '.o_notebook_content .o_data_cell:contains("Member")',
            content: "check if demo user has a 'Member' access",
        },
        {
            trigger: 'a.nav-link[name="access_rights"]',
            content: "show Administrator",
            run: "click",
        },
        {
            trigger: '.o_field_radio[name="role"] input[data-value="admin"]',
            content: "Add 'Administrator' access to demo user",
            run: `click`,
        },
        {
            trigger: 'a.nav-link[name="technical_access_rights"]',
            content: "show changes in Technical Administrator",
            run: "click",
        },
        {
            trigger: '.o_notebook_content .o_data_cell:contains("Administrator")',
            content: "check if demo user have 'Settings' with 'Administrator' level",
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
            trigger: '.o_field_radio[name="role"] input[data-value="admin"]:checked',
            content: "check if demo user have 'Settings' with 'Administrator' level",
        },
        {
            trigger: 'a.nav-link[name="technical_access_rights"]',
            content: "show Technical Administrator",
            run: "click",
        },
        {
            trigger: '.o_notebook_content .o_data_cell:contains("Administrator")',
            content: "check if demo user have 'Settings' with 'Administrator' level",
        },
    ],
});
