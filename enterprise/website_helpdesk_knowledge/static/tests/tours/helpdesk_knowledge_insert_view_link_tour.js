/** @odoo-module */

import { endKnowledgeTour } from '@knowledge/../tests/tours/knowledge_tour_utils';
import { registry } from "@web/core/registry";


registry.category("web_tour.tours").add('helpdesk_insert_kanban_view_link_in_knowledge', {
    url: '/odoo/action-helpdesk.helpdesk_ticket_action_main_tree',
    steps: () => [{ // switch to the kanban view
    trigger: 'button.o_switch_view.o_kanban',
    run: 'click',
}, { // wait for the kanban view to load
    trigger: '.o_kanban_renderer',
}, { // open the search bar menu
    trigger: '.o_control_panel .o_searchview_dropdown_toggler',
    run: "click",
}, { // pick a filter
    trigger: '.o_filter_menu .dropdown-item:contains("My Tickets")',
    run: "click",
}, { // check that the facet is now active
    trigger: '.o_searchview .o_facet_value:contains("My Tickets")',
}, { // open the cog menu
    trigger: '.o_control_panel .o_cp_action_menus .dropdown-toggle',
    run: "click",
}, { // open the knowledge submenu
    trigger: ".dropdown-menu .dropdown-toggle:contains(Knowledge)",
    run: "hover",
}, { // insert the view link in an article
    trigger: '.dropdown-menu .dropdown-item:contains("Insert link in article")',
    run: "click",
}, { // create a new article
    trigger: '.modal-footer button:contains("New")',
    run: 'click',
}, { // wait for Knowledge to open
    trigger: '.o_knowledge_form_view',
}, { // open the popover
    trigger: "[data-embedded='viewLink'] a",
    run: "click",
}, { // the user should be redirected to the new article
    trigger: "div.o_popover > div:nth-child(1) > div:contains('All Tickets')",
    run: "click",
}, { // check that the user is redirected to the view
    trigger: '.o_kanban_renderer',
}, { // check that the view has the selected facet
    trigger: '.o_searchview .o_facet_value:contains("My Tickets")',
}, { // check the title of the view
    trigger: '.o_control_panel .o_last_breadcrumb_item:contains("Tickets")',
}, {
    trigger: '.o_back_button',
    run: "click",
}, {
    trigger: '[data-embedded="viewLink"]',
}, ...endKnowledgeTour()
]});
