/** @odoo-module */

import { endKnowledgeTour } from './knowledge_tour_utils.js';
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
/**
 * This tour checks that a user that has readonly access on an article cannot
 * create items from the item kanban.
 */
registry.category("web_tour.tours").add('knowledge_readonly_item_kanban_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), { // open the Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
}, { // scroll to the embedded view to load it
    trigger: '.o_knowledge_behavior_type_embedded_view',
    run: function () {
        this.$anchor[0].scrollIntoView();
    },
}, { // wait for the kanban view to be mounted
    trigger: '.o_knowledge_behavior_type_embedded_view .o_kanban_renderer',
    run: () => {},
}, { // check that the "new" button is not shown
    trigger: '.o_control_panel_main:not(:has(.o-kanban-button-new))',
    run: () => {},
}, ...endKnowledgeTour()
]});
