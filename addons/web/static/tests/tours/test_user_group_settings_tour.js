import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_user_group_settings", {
    url: "/odoo/settings?debug=assets,tests",
    steps: () => [
        // create new privileges
        {
            trigger: 'button[data-menu-xmlid="base.menu_users"]',
            content: "open user menu",
            run: "click",
        },
        {
            trigger: 'a[data-menu-xmlid="base.menu_action_res_groups_privilege"]',
            content: "open privilege menu",
            run: "click",
        },
        {
            trigger: 'th.o_group_name:contains("Master Data")',
        },
        {
            trigger: 'button.o_list_button_add',
            content: "click on new button",
            run: "click",
        },
        {
            trigger: '.o_field_char[name="name"] input',
            content: "insert a privilege name",
            run: "fill Privi Foo",
        },
        {
            trigger: '.o_field_x2many_list_row_add a',
            content: "add groups (open modal)",
            run: "click",
        },
        {
            trigger: '.o_create_button',
            content: "create the first group",
            run: "click",
        },
        {
            trigger: '.o_field_char[name="name"] input[placeholder="Group Name"]',
            content: "insert the first group name",
            run: "fill Bar User",
        },
        {
            trigger: 'footer .o_form_button_save_new',
            content: "create the second group",
            run: "click",
        },
        {
            trigger: '.o_field_char[name="name"] input[placeholder="Group Name"]',
            content: "insert the second group name",
            run: "fill Bar Manager",
        },
        {
            trigger: 'a[name="inherit_groups"]',
            content: "get implied groups",
            run: "click",
        },
        {
            trigger: 'div[name="implied_ids"] .o_field_x2many_list_row_add a',
            content: "switch to implied",
            run: "click",
        },
        {
            trigger: '.o_searchview_input',
            content: "click on search bar",
            run: "click",
        },
        {
            trigger: '.o_searchview_input',
            content: "search 'Bar' groups",
            run: "fill Bar",
        },
        {
            trigger: ".o_searchview_autocomplete .o-dropdown-item.focus",
            content: "Validate search",
            run: "click",
        },
        {
            trigger: '.o_data_cell:contains("Bar User"):last',
            content: "click to implied group 'Bar User'",
            run: "click",
        },
        {
            trigger: 'footer .o_form_button_save',
            content: "save group and close modal",
            run: "click",
        },
        // and the new manager group to the demo user
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
            trigger: '.o_last_breadcrumb_item:contains("Marc Demo")',
            content: "check if is demo user",
        },
        {
            trigger: '.o_field_widget[name="group_ids"] .o_cell:has(label:contains("Privi Foo")) + .o_cell select',
            content: "Add 'Bar Manager' access to demo user",
            run: `selectByLabel Bar Manager`,
        },
        // open group information button (popover)
        {
            trigger: '.o_field_widget[name="group_ids"] .o_cell:has(label:contains("Privi Foo")) + .o_cell .o_group_info_button',
            content: "open group information for the new group",
            run: "click",
        },
        {
            trigger: '.o_popover:contains("Privi Foo") a:contains("Bar Manager")',
            content: "open the group from the info button",
            run: "click",
        },
        // check if demo user has this group
        {
            trigger: '.o_last_breadcrumb_item:contains("Bar Manager")',
            content: "check if is Bar Manager group",
        },
        {
            trigger: '.o_field_many2many[name="user_ids"] .o_data_cell:contains("Marc Demo")',
            content: "check if demo user has this group",
        },
    ],
});
