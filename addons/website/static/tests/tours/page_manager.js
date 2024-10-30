/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';
import { registry } from "@web/core/registry";

// TODO: This part should be moved in a QUnit test
const checkKanbanGroupBy = [{
    content: "Click on Kanban View",
    trigger: '.o_cp_switch_buttons .o_kanban',
}, {
    content: "Open search panel menu",
    extra_trigger: '.o_kanban_renderer',
    trigger: '.o_control_panel .o_searchview_dropdown_toggler',
}, {
    content: "Select 'Active' in the select of Add Custom Group",
    trigger: ".o_add_custom_group_menu",
    run: "text active",
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
	content: "Click on the search options",
	trigger: ".o_searchview_dropdown_toggler",
}, {
	content: "Select Test Website",
	trigger: ".o_dropdown_container.o_website_menu > .dropdown-item:contains('Test Website')",
}, {
	content: "Check that the homepage is now the one of Test Website",
	trigger: ".o_list_table .o_data_row .o_data_cell[name=name]:contains('Home') " +
			 "~ .o_data_cell[name=website_id]:contains('Test Website')",
	run: () => null, // it's a check
}, {
	content: "Check that the search options are still open",
	trigger: ".o_search_bar_menu",
	run: () => null, // it's a check
}, {
	content: "Go back to My Website",
	trigger: ".o_dropdown_container.o_website_menu > .dropdown-item:contains('My Website')",
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
}, () => [
    {
        content: "Click on Site",
        trigger: 'button.dropdown-toggle[data-menu-xmlid="website.menu_site"]',
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

wTourUtils.registerWebsitePreviewTour('website_page_manager_session_forced', {
    test: true,
    url: '/',
}, () => [...wTourUtils.testSwitchWebsite('Test Website'), {
    content: "Click on Site",
    trigger: 'button.dropdown-toggle[data-menu-xmlid="website.menu_site"]',
}, {
    content: "Click on Pages",
    trigger: 'a.dropdown-item[data-menu-xmlid="website.menu_website_pages_list"]',
}, {
    content: "Check that the homepage is the one of Test Website",
    trigger: ".o_list_table .o_data_row .o_data_cell[name=name]:contains('Home') " +
             "~ .o_data_cell[name=website_id]:contains('Test Website')",
    run: () => null, // it's a check
}, {
	content: "Click on the search options",
	trigger: ".o_searchview_dropdown_toggler",
}, {
	content: "Check that the selected website is Test Website",
	trigger: ".o_dropdown_container.o_website_menu > .dropdown-item:contains('Test Website')",
    run: () => null, // it's a check
}]);

registry.category("web_tour.tours").add('website_page_manager_direct_access', {
    test: true,
    url: '/web#action=website.action_website_pages_list',
    steps: () => [{
    content: "Check that the homepage is the one of Test Website",
    trigger: ".o_list_table .o_data_row .o_data_cell[name=name]:contains('Home') " +
             "~ .o_data_cell[name=website_id]:contains('Test Website')",
    run: () => null, // it's a check
}, {
	content: "Click on the search options",
	trigger: ".o_searchview_dropdown_toggler",
}, {
	content: "Check that the selected website is Test Website",
	trigger: ".o_dropdown_container.o_website_menu > .dropdown-item:contains('Test Website')",
    run: () => null, // it's a check
}]});
