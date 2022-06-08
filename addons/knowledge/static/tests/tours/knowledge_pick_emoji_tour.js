/** @odoo-module */

import tour from 'web_tour.tour';

tour.register('knowledge_pick_emoji_tour', {
    test: true,
    url: '/web',
}, [tour.stepUtils.showAppsMenuItem(), {
    // open Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
}, {
    // click on the main "Create" action
    trigger: '.o_knowledge_header .btn:contains("Create")',
}, {
    trigger: 'section[data-section="private"] .o_article .o_article_name:contains("New Article")',
    run: () => {}, // check that the article is correctly created (private section)
}, {
    trigger: '.o_knowledge_icon_cover_buttons',
    run: () => {
        // force the cover buttons to be visible (it's only visible on hover)
        $('.o_knowledge_add_icon, .o_knowledge_add_cover').css({
            opacity: 1,
            visibility: 'visible'
        });
    },
}, {
    // add a random emoji
    trigger: '.o_knowledge_add_icon',
    run: 'click',
}, {
    trigger: '.o_knowledge_body .o_article_emoji',
    run: 'click',
}, {
    trigger: '.o_article_emoji_dropdown_panel span[data-unicode="😃"]',
    run: 'click',
}, {
    // check that the emoji has been properly changed in the article body
    trigger: '.o_knowledge_body .o_article_emoji:contains(😃)',
    run: () => {},
}, {
    // check that the emoji has been properly changed in the header
    trigger: '.o_knowledge_header .o_article_emoji:contains(😃)',
    run: () => {},
}, {
    // check that the emoji has been properly changed in the aside block
    trigger: '.o_knowledge_aside .o_article_emoji_active:contains(😃)',
    run: () => {}
}]);
