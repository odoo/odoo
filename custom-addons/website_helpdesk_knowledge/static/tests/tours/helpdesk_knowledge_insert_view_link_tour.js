/** @odoo-module */

import { endKnowledgeTour } from '@knowledge/../tests/tours/knowledge_tour_utils';
import { registry } from "@web/core/registry";


registry.category("web_tour.tours").add('helpdesk_insert_kanban_view_link_in_knowledge', {
    url: '/web#action=helpdesk.helpdesk_ticket_action_main_tree',
    test: true,
    steps: () => [{ // switch to the kanban view
    trigger: 'button.o_switch_view.o_kanban',
    run: 'click',
}, { // wait for the kanban view to load
    trigger: '.o_kanban_renderer',
}, { // open the search bar menu
    trigger: '.o_control_panel .o_searchview_dropdown_toggler',
}, { // pick a filter
    trigger: '.o_filter_menu .dropdown-item:contains("My Tickets")',
}, { // check that the facet is now active
    trigger: '.o_searchview .o_facet_value:contains("My Tickets")',
    run: () => {},
}, { // open the cog menu
    trigger: '.o_control_panel .o_cp_action_menus .dropdown-toggle',
}, { // open the knowledge submenu
    trigger: ".o_control_panel .o_cp_action_menus .dropdown-toggle:contains(Knowledge)",
    run: function () {
        this.$anchor[0].dispatchEvent(new MouseEvent("mouseenter"));
    },
}, { // insert the view link in an article
    trigger: '.o_cp_action_menus .dropdown-item:contains("Insert link in article")',
}, { // create a new article
    trigger: '.modal-footer button:contains("New")',
    run: 'click',
}, { // wait for Knowledge to open
    trigger: '.o_knowledge_form_view',
}, { // the user should be redirected to the new article
    trigger: '.o_knowledge_behavior_type_view_link',
    run: 'dblclick',
}, { // check that the user is redirected to the view
    trigger: '.o_kanban_renderer',
}, { // check that the view has the selected facet
    trigger: '.o_searchview .o_facet_value:contains("My Tickets")',
}, { // check the title of the view
    trigger: '.o_control_panel .o_last_breadcrumb_item:contains("Tickets")',
}, {
    trigger: '.o_back_button'
}, {
    trigger: '.o_knowledge_behavior_type_view_link',
    run: () => {}
}, ...endKnowledgeTour()
]});
