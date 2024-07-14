/** @odoo-module */

import { endKnowledgeTour } from '@knowledge/../tests/tours/knowledge_tour_utils';
import { registry } from "@web/core/registry";


registry.category("web_tour.tours").add('helpdesk_insert_graph_view_in_knowledge', {
    url: '/web#action=helpdesk.helpdesk_ticket_analysis_action',
    test: true,
    steps: () => [{ // open the search menu
    trigger: '.o_control_panel .o_searchview_dropdown_toggler',
}, { // pick a filter
    trigger: '.o_filter_menu .dropdown-item:contains("Urgent")',
}, { // check that the facet is now active
    trigger: '.o_searchview .o_facet_value:contains("Urgent")',
},{ // reopen the search menu
    trigger: '.o_control_panel .o_searchview_dropdown_toggler',
}, { // pick a group by
    trigger: '.o_group_by_menu .dropdown-item:contains("Team")',
}, { // check that the facet is now active
    trigger: '.o_searchview .o_facet_value:contains("Team")',
}, { // open the cog menu
    trigger: '.o_control_panel .o_cp_action_menus .dropdown-toggle',
}, { // open the knowledge submenu
    trigger: ".o_control_panel .o_cp_action_menus .dropdown-toggle:contains(Knowledge)",
    run: function () {
        this.$anchor[0].dispatchEvent(new MouseEvent("mouseenter"));
    },
}, { // insert the view in an article
    trigger: '.o_cp_action_menus .dropdown-item:contains("Insert view in article")',
}, { // create a new article
    trigger: '.modal-footer button:contains("New")',
}, { // wait for Knowledge to open
    trigger: '.o_knowledge_form_view',
}, { // the user should be redirected to the new article
    trigger: '.o_knowledge_behavior_type_embedded_view',
    run: function () {
        this.$anchor[0].scrollIntoView();
    },
}, { // check that the embedded view has the selected facet
    trigger: '.o_knowledge_behavior_type_embedded_view .o_searchview .o_facet_value:contains("Urgent")',
}, {
    trigger: '.o_knowledge_behavior_type_embedded_view .o_searchview .o_facet_value:contains("Team")',
}, ...endKnowledgeTour()
]});
