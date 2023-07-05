/** @odoo-module **/

import wTourUtils from 'website.tour_utils';

// TODO: This part should be moved in a QUnit test
const checkKanbanGroupBy = [{
    content: "Click on Kanban View",
    trigger: '.o_cp_switch_buttons .o_kanban',
}, {
    content: "Click on Group By",
    extra_trigger: '.o_kanban_renderer',
    trigger: '.o_search_options .o_group_by_menu button',
}, {
    content: "Click on Add Custom Group",
    trigger: '.o_search_options .o_add_custom_group_menu button',
    run: function (actions) {
        this.$anchor[0].dispatchEvent(new MouseEvent('mouseenter'));
    },
}, {
    content: "Click on Apply", // Active is selected by default
    trigger: '.o_add_custom_group_menu .dropdown-menu .btn-primary',
}, {
    content: "Click on List View",
    extra_trigger: '.o_kanban_renderer .o_kanban_header',
    trigger: '.o_cp_switch_buttons .o_list',
}, {
    content: "Remove applied Group By",
    extra_trigger: '.o_list_renderer',
    trigger: '.o_cp_searchview .o_facet_remove',
}];

const checkWebsiteFilter = [{
    content: "Click on My Website",
    trigger: "button.dropdown-toggle:contains('My Website')",
}, {
    content: "Select My Website 2",
    trigger: ".dropdown-menu.show > .dropdown-item:contains('My Website 2')",
}, {
    content: "Check that the homepage is now the one of My Website 2",
    trigger: ".o_list_table .o_data_row .o_data_cell[name=name]:contains('Home') " +
             "~ .o_data_cell[name=website_id]:contains('My Website 2')",
    run: () => null, // it's a check
}, {
    content: "Click on My Website 2",
    trigger: "button.dropdown-toggle:contains('My Website 2')",
}, {
    content: "Go back to My Website",
    trigger: ".dropdown-menu.show > .dropdown-item:contains('My Website')",
}, {
    content: "Check that the homepage is now the one of My Website",
    trigger: ".o_list_table .o_data_row .o_data_cell[name=name]:contains('Home') " +
             "~ .o_data_cell[name=website_id]:contains('My Website'):not(:contains('2'))",
    run: () => null, // it's a check
}];

const deleteSelectedPage = [
    {
        content: "Click on Action",
        trigger: '.o_cp_action_menus button',
    },
    {
        content: "Click on Delete",
        trigger: '.o-dropdown--menu span:contains("Delete")',
    },
    {
        content: "Click on I am sure about this",
        trigger: 'main.modal-body input[type="checkbox"]',
        // The loading of the dependencies can take a while and
        // sometimes reach the default 10s timeout
        timeout: 20000,
    },
    {
        content: "Click on OK",
        trigger: '.modal-content footer button.btn-primary:not([disabled])',
    }
];
const homePage = 'tr:contains("Home")';

wTourUtils.registerWebsitePreviewTour('website_page_manager', {
    test: true,
    url: '/',
}, [
    {
        content: "Click on Site",
        trigger: 'button.dropdown-toggle[title="Site"]',
    },
    {
        content: "Click on Pages",
        trigger: 'a.dropdown-item[data-menu-xmlid="website.menu_website_pages_list"]',
    },
    ...checkKanbanGroupBy,
    ...checkWebsiteFilter,
    {
        content: "Click on Home Page",
        trigger: `.o_list_renderer ${homePage} td.o_list_record_selector input[type="checkbox"]`,
    },
    ...deleteSelectedPage,
    {
        content: "Check that the page has been removed",
        trigger: `.o_list_renderer:not(:has(${homePage}))`,
        run: () => null,
    },
    {
        content: "Click on All Pages",
        trigger: '.o_list_renderer thead input[type="checkbox"]',
    },
    ...deleteSelectedPage,
    {
        content: "Check that all pages have been removed",
        trigger: '.o_list_renderer tbody:not(:has([data-id]))',
        run: () => null,
    },
]);
