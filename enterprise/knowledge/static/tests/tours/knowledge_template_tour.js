/** @odoo-module */

import { endKnowledgeTour } from './knowledge_tour_utils.js';
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";


registry.category("web_tour.tours").add("knowledge_load_template", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(), {
            // open the Knowledge App
            trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
            run: "click",
        }, { // click on the main "New" action
            trigger: '.o_knowledge_header .btn:contains("New")',
            run: "click",
        }, { // open the template picker dialog
            trigger: '.o_knowledge_helper .o_knowledge_load_template',
            run: "click",
        }, { // choose a template
            trigger: '.o_knowledge_template_selector div:contains("My Template")',
            run: "click",
        }, { // insert the template
            trigger: 'button:contains("Load Template")',
            run: "click",
        }, { // check that the icon has been changed
            trigger: '.o_knowledge_body .o_article_emoji:contains(📚)',
        }, { // check that the title of the article has changed
            trigger: '.o_hierarchy_article_name input:value("My Template")',
        }, { // check that the body of the article has changed
            trigger: '.o_knowledge_body .note-editable:contains(Lorem ipsum dolor sit amet, consectetur adipisicing elit.)',
        }, ...endKnowledgeTour()
    ]
});
