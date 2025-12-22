/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_website_page_manager', {
    url: '/odoo/action-test_website.action_test_model_multi_website',
    steps: () => [
// Part 1: check that the website filter is working
{
    content: "Check that we see records from My Website",
    trigger: ".o_list_table .o_data_row .o_data_cell[name=name]:contains('Test Multi Model Website 1') " +
             "~ .o_data_cell[name=website_id]:contains('My Website')",
}, {
    content: "Check that there is only 2 records in the pager",
    trigger: ".o_pager .o_pager_value:contains('1-2')",
}, {
    content: "Click on the 'Select all records' checkbox",
    trigger: "thead .o_list_record_selector",
    run: "click",
}, {
    content: "Check that there is only 2 records selected",
    trigger: ".o_list_selection_box:contains(2):contains(selected)",
}, {
    content: "Click on the 'Select all records' checkbox again to unselect all records and see the search bar",
    trigger: "thead .o_list_record_selector",
    run: "click",
}, {
	content: "Click on the search options",
	trigger: ".o_searchview_dropdown_toggler",
    run: "click",
}, {
    content: "Select My Website 2",
    trigger: ".o_dropdown_container.o_website_menu > .dropdown-item:contains('My Website 2')",
    run: "click",
}, {
    // This step is just here to ensure there is more records than the 2
    // available on website 1, to ensure the test is actually testing something.
    content: "Check that we see records from My Website 2",
    trigger: ".o_list_table .o_data_row .o_data_cell[name=name]:contains('Test Model Multi Website 2') " +
             "~ .o_data_cell[name=website_id]:contains('My Website 2')",
},
// Part 2: ensure Kanban View is working / not crashing
{
    content: "Click on Kanban View",
    trigger: '.o_cp_switch_buttons .o_kanban',
    run: "click",
},
{
    trigger: ".o_kanban_renderer",
},
{
    content: "Click on List View",
    trigger: '.o_cp_switch_buttons .o_list',
    run: "click",
}, {
    content: "Wait for List View to be loaded",
    trigger: '.o_list_renderer',
}]
});

registry.category("web_tour.tours").add('test_website_page_manager_js_class_bug', {
    url: '/odoo/action-test_website.action_test_model_multi_website_js_class_bug',
    steps: () => [
{
    content: "Click on Kanban View",
    trigger: '.o_cp_switch_buttons .o_kanban',
    run: "click",
}, {
    content: "Wait for Kanban View to be loaded",
    trigger: '.o_kanban_renderer',
}]
});

registry.category("web_tour.tours").add('test_website_page_manager_no_website_id', {
    url: '/odoo/action-test_website.action_test_model',
    steps: () => [
{
    content: "Click on Kanban View",
    trigger: '.o_cp_switch_buttons .o_kanban',
    run: "click",
}, {
    content: "Wait for Kanban View to be loaded",
    trigger: '.o_kanban_renderer',
}]
});
