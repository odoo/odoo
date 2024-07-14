/** @odoo-module */

import { registry } from "@web/core/registry";
import { endKnowledgeTour, openCommandBar } from '../knowledge_tour_utils.js';
import { stepUtils } from "@web_tour/tour_service/tour_utils";


registry.category("web_tour.tours").add('knowledge_index_command_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    // open the Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
}, { // open the command bar
    trigger: '.odoo-editor-editable > p',
    run: function () {
        openCommandBar(this.$anchor[0]);
    },
}, { // click on the /index command
    trigger: '.oe-powerbox-commandName:contains("Index")',
    run: 'click',
}, { // wait for the block to appear in the editor
    trigger: '.o_knowledge_behavior_type_articles_structure',
}, { // click on the refresh button
    trigger: '.o_knowledge_behavior_type_articles_structure button[title="Update"]',
    run: 'click',
}, { // click on the switch mode button
    trigger: '.o_knowledge_behavior_type_articles_structure button[title="Switch Mode"]',
    run: 'click',
}, ...endKnowledgeTour()
]});
