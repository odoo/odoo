/** @odoo-module */

import { endKnowledgeTour } from './knowledge_tour_utils.js';
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";


registry.category("web_tour.tours").add("knowledge_load_template", {
    url: "/web",
    test: true,
    steps: () => [
        stepUtils.showAppsMenuItem(), {
            // open the Knowledge App
            trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
        }, { // click on the main "New" action
            trigger: '.o_knowledge_header .btn:contains("New")',
        }, { // open the template picker dialog
            trigger: '.o_knowledge_helper .o_knowledge_load_template',
        }, { // choose a template
            trigger: '.o_knowledge_template_selector div:contains("My Template")',
        }, { // insert the template
            trigger: 'button:contains("Load Template")'
        }, { // check that the icon has been changed
            trigger: '.o_knowledge_body .o_article_emoji:contains(📚)',
            run: () => {},
        }, { // check that the title of the article has changed
            trigger: '.o_breadcrumb_article_name_container:contains("My Template")',
            run: () => {},
        }, { // check that the body of the article has changed
            trigger: '.o_knowledge_body .note-editable:contains(Lorem ipsum dolor sit amet, consectetur adipisicing elit.)',
            run: () => {},
        }, ...endKnowledgeTour()
    ]
});
