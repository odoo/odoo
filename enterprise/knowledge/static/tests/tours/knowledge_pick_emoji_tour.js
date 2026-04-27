/** @odoo-module */

import { endKnowledgeTour } from '@knowledge/../tests/tours/knowledge_tour_utils';
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('knowledge_pick_emoji_tour', {
    url: '/odoo',
    steps: () => [stepUtils.showAppsMenuItem(), {
    // open Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
    run: "click",
}, {
    // click on the main "New" action
    trigger: '.o_knowledge_header .btn:contains("New")',
    run: "click",
}, {
    trigger: 'section[data-section="private"] .o_article .o_article_name:contains("Untitled")',
 // check that the article is correctly created (private section)
}, {
    trigger: '#dropdown_tools_panel',
    run: "click",
}, {
    // add a random emoji
    trigger: '.o_knowledge_add_icon',
    run: 'click',
}, {
    trigger: '.o_knowledge_body .o_article_emoji',
    run: 'click',
}, {
    trigger: '.o-Emoji[data-codepoints="😃"]',
    run: 'click',
}, {
    // check that the emoji has been properly changed in the article body
    trigger: '.o_knowledge_body .o_article_emoji:contains(😃)',
}, {
    // check that the emoji has been properly changed in the header
    trigger: '.o_knowledge_header .o_article_emoji:contains(😃)',
}, {
    // check that the emoji has been properly changed in the aside block
    trigger: '.o_knowledge_sidebar .o_article_emoji:contains(😃)',
}, ...endKnowledgeTour()
]});
