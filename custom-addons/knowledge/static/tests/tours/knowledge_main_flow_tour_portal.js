/** @odoo-module */

/**
 * Global Knowledge flow tour - Adapter for portal user
 * Features tested:
 * - Create a private article
 * - Change its title / content
 * - Write on a "workspace" article to which we have access
 * - Create children articles to a "workspace" article to which we have access
 * - Favorite 2 different articles and invert their order in the favorite section
 */

import { dragAndDropArticle } from '@knowledge/../tests/tours/knowledge_tour_utils';
import { registry } from "@web/core/registry";


registry.category("web_tour.tours").add('knowledge_main_flow_tour_portal', {
    test: true,
    url: '/knowledge/home',
    steps: () => [{
    // click on the main "New" action
    trigger: '.o_knowledge_header .btn:contains("New")',
}, {
    trigger: 'section[data-section="private"] .o_article .o_article_name:contains("Untitled")',
    run: () => {},  // check that the article is correctly created (private section)
}, {
    trigger: '.o_breadcrumb_article_name > input',
    run: 'text My Private Article',  // modify the article name
}, {
    trigger: '.note-editable.odoo-editor-editable',
    run: 'text Content of My Private Article',  // modify the article content
}, {
    trigger: 'body',
    run: () => {
        // Make sure the internal article is not visible
        if (document.querySelectorAll(
            'section[data-section="workspace"] .o_article .o_article_name'
        ).length !== 1) {
            throw new Error("Internal Workspace Article is not supposed to be visible for portal user.");
        }
    }
}, {
    trigger: '#knowledge_search_bar' // make sure the search article feature works
}, {
    trigger: '.o_select_menu_item:contains("Workspace Article")',
    in_modal: false,
}, {
    trigger: 'button:contains("Open")'
}, {
    trigger: '.o_knowledge_editor:contains("Content of Workspace Article")',
    run: () => {},  // wait for article to be correctly loaded
}, {
    trigger: '.note-editable.odoo-editor-editable',
    run: 'text Edited Content of Workspace Article',  // modify the article content
}, {
    trigger: '.o_article:contains("Workspace Article")',
    run: () => {
        // force the create button to be visible (it's only visible on hover)
        $('.o_article:contains("Workspace Article") a.o_article_create').css('display', 'block');
    },
}, {
    // create child article
    trigger: '.o_article:contains("Workspace Article") a.o_article_create',
}, {
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Untitled")',
    run: () => {},  // check that the article is correctly created (workspace section)
}, {
    trigger: '.o_breadcrumb_article_name > input',
    run: 'text Child Article 1',  // modify the article name
}, {
    // create child article (2)
    trigger: '.o_article:contains("Workspace Article") a.o_article_create',
}, {
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Untitled")',
    run: () => {},  // check that the article is correctly created (workspace section)
}, {
    trigger: '.o_breadcrumb_article_name > input',
    run: 'text Child Article 2',  // modify the article name
}, {
    // go back to main workspace article
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Workspace Article")',
}, {
    trigger: '.o_knowledge_editor:contains("Edited Content of Workspace Article")',
    run: () => {},  // wait for article to be correctly loaded
}, {
    // add to favorite
    trigger: '.o_knowledge_toggle_favorite',
}, {
    // check article was correctly added into favorites
    trigger: 'div.o_favorite_container .o_article .o_article_name:contains("Workspace Article")',
    run: () => {},
}, {
    // go back to private article
    trigger: 'section[data-section="private"] .o_article .o_article_name:contains("My Private Article")',
}, {
    trigger: '.o_knowledge_editor:contains("My Private Article")',
    run: () => {},  // wait for article to be correctly loaded
}, {
    // add to favorite
    trigger: '.o_knowledge_toggle_favorite',
}, {
    // wait for the article to be registered as favorited
    trigger: '.o_knowledge_toggle_favorite .fa-star',
    run: () => {},
}, {
    // move private article above workspace article in the favorite section
    trigger: 'div.o_favorite_container .o_article_handle:contains("My Private Article")',
    run: () => {
        dragAndDropArticle(
            $('div.o_favorite_container .o_article_handle:contains("My Private Article")'),
            $('div.o_favorite_container .o_article_handle:contains("Workspace Article")'),
        );
    },
}, {
    // verify that the move was done
    trigger: 'div.o_favorite_container ul > :eq(0):contains("My Private Article")',
    isCheck: true,
}]});
