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
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

let workspaceArticleResId;
let privateArticleResId;

/**
 * Extract the resId from a Knowledge portal URL of scheme:
 * /knowledge/article/{resId}
 * @param {URL} url
 * @returns {Number} resId
 */
function extractURLResID(url) {
    return parseInt((url.pathname.match("/knowledge/article/([0-9]+)") || []).at(1));
}

registry.category("web_tour.tours").add('knowledge_main_flow_tour_portal', {
    url: '/knowledge/home',
    steps: () => [{
    // click on the main "New" action
    trigger: '.o_knowledge_header .btn:contains("New")',
    run: (actionHelper) => {
        const url = new URL(browser.location);
        workspaceArticleResId = extractURLResID(url);
        if (!workspaceArticleResId) {
            throw new Error(`Expected pathname to be like /knowledge/article/{id}, got ${url.pathname} instead.`);
        }
        actionHelper.click();
    },
}, {
    trigger: 'section[data-section="private"] .o_article .o_article_name:contains("Untitled")',
    run: () => {
        const url = new URL(browser.location);
        const resId = extractURLResID(url);
        if (resId !== workspaceArticleResId + 1) {
            throw new Error(`Expected pathname to be like /knowledge/article/${workspaceArticleResId + 1}, got ${url.pathname} instead.`);
        }
    },  // check that the article is correctly created (private section)
}, {
    trigger: '.o_hierarchy_article_name > input',
    run: "edit My Private Article && click body",  // modify the article name
}, {
    trigger: '.note-editable.odoo-editor-editable',
    run: "editor Content of My Private Article",  // modify the article content
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
    trigger: '#knowledge_search_bar', // make sure the search article feature works
    run: "click",
}, {
    trigger: '.o_select_menu_item:contains("Workspace Article")',
    run: "click",
}, {
    trigger: 'button:contains("Open")',
    run: "click",
}, {
    trigger: '.o_knowledge_editor:contains("Content of Workspace Article")',
  // wait for article to be correctly loaded
}, {
    trigger: '.note-editable.odoo-editor-editable',
    run: "editor Edited Content of Workspace Article",  // modify the article content
}, {
    content: "Hover on Workspace Article to make create article visible",
    trigger: ".o_article:contains(Workspace Article)",
    run: "hover && click .o_article:contains(Workspace Article) a.o_article_create",
}, {
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Untitled")',
  // check that the article is correctly created (workspace section)
}, {
    trigger: '.o_hierarchy_article_name > input',
    run: "edit Child Article 1 && click body",  // modify the article name
}, 
{
    content: "create child article (2)",
    trigger: ".o_article:contains(Workspace Article)",
    run: "hover && click .o_article:contains(Workspace Article) a.o_article_create",
},
{
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Untitled")',
  // check that the article is correctly created (workspace section)
}, {
    trigger: '.o_hierarchy_article_name > input',
    run: "edit Child Article 2 && click body",  // modify the article name
}, {
    // go back to main workspace article
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Workspace Article")',
    run: "click",
}, {
    trigger: '.o_knowledge_editor:contains("Edited Content of Workspace Article")',
  // wait for article to be correctly loaded
}, {
    // add to favorite
    trigger: '.o_knowledge_toggle_favorite',
    run: "click",
}, {
    // check article was correctly added into favorites
    trigger: 'div.o_favorite_container .o_article .o_article_name:contains("Workspace Article")',
}, {
    // go back to private article
    trigger: 'section[data-section="private"] .o_article .o_article_name:contains("My Private Article")',
    run: "click",
}, {
    trigger: '.o_knowledge_editor:contains("My Private Article")',
    run: () => {
        privateArticleResId = extractURLResID(new URL(browser.location));
        if (privateArticleResId === workspaceArticleResId) {
            throw new Error(`Expected private article resId ${privateArticleResId} to be different from workspace article resId ${workspaceArticleResId}.`);
        }
        browser.history.back();
    },  // wait for article to be correctly loaded and go back in the browser history
}, {
    trigger: '.o_knowledge_editor:contains("Edited Content of Workspace Article")',
    run: () => {
        const resId = extractURLResID(new URL(browser.location));
        if (resId !== workspaceArticleResId) {
            throw new Error(`Expected to be back on the workspace article with resId ${workspaceArticleResId}, got ${resId} instead.`)
        }
        browser.history.forward();
    },  // wait for article to be correctly loaded and go forward in the browser history
}, {
    trigger: '.o_knowledge_editor:contains("My Private Article")',
    run: () => {
        const resId = extractURLResID(new URL(browser.location));
        if (resId !== privateArticleResId) {
            throw new Error(`Expected to be back on the private article with resId ${privateArticleResId}, got ${resId} instead.`)
        }
    },  // wait for article to be correctly loaded
}, {
    // add to favorite
    trigger: '.o_knowledge_toggle_favorite',
    run: "click",
}, {
    // wait for the article to be registered as favorited
    trigger: '.o_knowledge_toggle_favorite .fa-star',
}, {
    // move private article above workspace article in the favorite section
    trigger: 'div.o_favorite_container .o_article_handle:contains("My Private Article")',
    run: () => {
        dragAndDropArticle(
            'div.o_favorite_container .o_article_handle:contains("My Private Article")',
            'div.o_favorite_container .o_article_handle:contains("Workspace Article")',
        );
    },
}, {
    // verify that the move was done
    trigger: 'div.o_favorite_container ul li:first:contains("My Private Article")',
}]});
