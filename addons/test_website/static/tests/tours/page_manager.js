/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('test_website_page_manager', {
    test: true,
    url: '/web#action=test_website.action_test_model_multi_website',
}, [
// Part 1: check that the website filter is working
{
    content: "Check that we see records from My Website",
    trigger: ".o_list_table .o_data_row .o_data_cell[name=name]:contains('Test Multi Model Website 1') " +
             "~ .o_data_cell[name=website_id]:contains('My Website')",
    run: () => null, // it's a check
}, {
    content: "Check that there is only 2 records in the pager",
    trigger: ".o_pager .o_pager_value:contains('1-2')",
    run: () => null, // it's a check
}, {
    content: "Click on the 'Select all records' checkbox",
    trigger: "thead .o_list_record_selector",
}, {
    content: "Check that there is only 2 records selected",
    trigger: ".o_list_selection_box:contains('2 selected')",
    run: () => null, // it's a check
}, {
    content: "Click on My Website search filter",
    trigger: "button.dropdown-toggle:contains('My Website')",
}, {
    content: "Select My Website 2",
    trigger: ".dropdown-menu.show > .dropdown-item:contains('My Website 2')",
}, {
    // This step is just here to ensure there is more records than the 2
    // available on website 1, to ensure the test is actually testing something.
    content: "Check that we see records from My Website 2",
    trigger: ".o_list_table .o_data_row .o_data_cell[name=name]:contains('Test Model Multi Website 2') " +
             "~ .o_data_cell[name=website_id]:contains('My Website 2')",
    run: () => null, // it's a check
},
// Part 2: ensure Kanban View is working / not crashing
{
    content: "Click on Kanban View",
    trigger: '.o_cp_switch_buttons .o_kanban',
}, {
    content: "Click on List View",
    extra_trigger: '.o_kanban_renderer',
    trigger: '.o_cp_switch_buttons .o_list',
}, {
    content: "Wait for List View to be loaded",
    trigger: '.o_list_renderer',
    run: () => null, // it's a check
}]);

tour.register('test_website_page_manager_js_class_bug', {
    test: true,
    url: '/web#action=test_website.action_test_model_multi_website_js_class_bug',
}, [{
    content: "Click on Kanban View",
    trigger: '.o_cp_switch_buttons .o_kanban',
}, {
    content: "Wait for Kanban View to be loaded",
    trigger: '.o_kanban_renderer',
    run: () => null, // it's a check
}]);

tour.register('test_website_page_manager_no_website_id', {
    test: true,
    url: '/web#action=test_website.action_test_model',
}, [{
    content: "Click on Kanban View",
    trigger: '.o_cp_switch_buttons .o_kanban',
}, {
    content: "Wait for Kanban View to be loaded",
    trigger: '.o_kanban_renderer',
    run: () => null, // it's a check
}]);

