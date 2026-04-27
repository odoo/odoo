/** @odoo-module */

import { registry } from "@web/core/registry";
import { edit, pointerDown } from "@odoo/hoot-dom";

/**
 * Returns the jQuery selector to find the nth element in the specified depth.
 * e.g: The 50th element of depth 1 would be "Child Article 49".
 *
 * @param {integer} n
 * @param {String} depth
 */
const getNthArticleSelector = (n, depth) => {
    let articleBaseName;
    if (depth === 0) {
        articleBaseName = 'Root Article';
    } else if (depth === 1) {
        articleBaseName = 'Child Article';
    } else {
        articleBaseName = 'Grand-Child Article';
    }

    // articles are index based so we subtract 1
    return `li.o_article:contains("${articleBaseName} ${n-1}")`;
};

/**
 * Advanced use case:
 *
 * The active article is within a hierarchy where itself is not within the 50 first articles
 * of its sub-tree but its ancestors are ALSO not within the 50 first articles of their own sub-tree.
 *
 * Check that everything is correctly displayed, notably the fact that we "force" the display
 * of the active article and its ancestors.
 *
 * The use case is as follows:
 * - 1 root article
 * - 254 children, all of which are children of "Root Article 0"
 * - 344 grand-children, all of which are children of "Child Article 203" (the 204th child article)
 *
 * When opening the tree, "Root Article 103", "Child Article 203" and "Grand-Child Article 218"
 * should all be forcefully displayed, even though outside of 50 first articles of their respective
 * sub-tree.
 */
const LOAD_MORE_ADVANCED_STEPS = [{
    trigger: 'input.knowledge_search_bar',
    async run(helpers) {
        await pointerDown(this.anchor);
        await edit("Grand-Child Article 218");
    }
}, {
    trigger: 'ul.o_search_tree .o_article a',
    run: "click",
}, {
    // check first article is displayed
    trigger: getNthArticleSelector(1, 0),
}, {
    // check second article ancestor is displayed (even though outside of 50 first)
    // it should be placed after the 50th child article and after the load more
    trigger: `${getNthArticleSelector(50, 1)} + .o_knowledge_article_load_more + ${getNthArticleSelector(204, 1)}`,
}, {
    // check the active article is displayed (even though outside of 50 first)
    // it should be placed after the 50th grand-child article and after the load more
    trigger: `${getNthArticleSelector(50, 2)} + .o_knowledge_article_load_more + ${getNthArticleSelector(219, 2)}`,
}, {
    // click on load more for the children articles
    trigger: `${getNthArticleSelector(50, 1)} + .o_knowledge_article_load_more`,
    run: "click",
}, {
    // check second article ancestor is displayed (even though outside of 100 first)
    // it should be placed after the 100th child article and after the load more
    trigger: `${getNthArticleSelector(100, 1)} + .o_knowledge_article_load_more + ${getNthArticleSelector(204, 1)}`,
}, {
    // click on load more for the children articles
    trigger: `${getNthArticleSelector(100, 1)} + .o_knowledge_article_load_more`,
    run: "click",
}, {
    // check second article ancestor is displayed (even though outside of 100 first)
    // it should be placed after the 150th child article and after the load more
    trigger: `${getNthArticleSelector(150, 1)} + .o_knowledge_article_load_more + ${getNthArticleSelector(204, 1)}`,
}, {
    // click on load more for the children articles
    trigger: `${getNthArticleSelector(150, 1)} + .o_knowledge_article_load_more`,
    run: "click",
}, {
    // check second article ancestor is displayed (even though outside of 100 first)
    // it should be placed after the 200th child article and after the load more
    trigger: `${getNthArticleSelector(200, 1)} + .o_knowledge_article_load_more + ${getNthArticleSelector(204, 1)}`,
}, {
    // click on load more for the children articles
    trigger: `${getNthArticleSelector(200, 1)} + .o_knowledge_article_load_more`,
    run: "click",
}, {
    // check second article ancestor is displayed (even though outside of 100 first)
    // it should be placed at its correct spot after 203
    trigger: `${getNthArticleSelector(203, 1)} + ${getNthArticleSelector(204, 1)}`,
}, {
    // click on load more for the grand-children articles
    trigger: `${getNthArticleSelector(50, 2)} + .o_knowledge_article_load_more`,
    run: "click",
}, {
    // check active article is displayed (even though outside of 100 first)
    // it should be placed after the 100th grand-child article and after the load more
    trigger: `${getNthArticleSelector(100, 2)} + .o_knowledge_article_load_more + ${getNthArticleSelector(219, 2)}`,
}, {
    // click on load more for the grand-children articles
    trigger: `${getNthArticleSelector(100, 2)} + .o_knowledge_article_load_more`,
    run: "click",
}, {
    // check active article is displayed (even though outside of 100 first)
    // it should be placed after the 150th grand-child article and after the load more
    trigger: `${getNthArticleSelector(150, 2)} + .o_knowledge_article_load_more + ${getNthArticleSelector(219, 2)}`,
}, {
    // click on load more for the grand-children articles
    trigger: `${getNthArticleSelector(150, 2)} + .o_knowledge_article_load_more`,
    run: "click",
}, {
    // check active article is displayed (even though outside of 100 first)
    // it should be placed after the 200th grand-child article and after the load more
    trigger: `${getNthArticleSelector(200, 2)} + .o_knowledge_article_load_more + ${getNthArticleSelector(219, 2)}`,
}, {
    // click on load more for the grand-children articles
    trigger: `${getNthArticleSelector(200, 2)} + .o_knowledge_article_load_more`,
    run: "click",
}, {
    // check active article is displayed (even though outside of 100 first)
    // it should be placed at its correct spot after 218
    trigger: `${getNthArticleSelector(218, 2)} + ${getNthArticleSelector(219, 2)}`,
}];

registry.category("web_tour.tours").add('website_knowledge_load_more_tour', {
    steps: () => [
        ...LOAD_MORE_ADVANCED_STEPS,
    ]
});
