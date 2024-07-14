/** @odoo-module */

import { registry } from "@web/core/registry";

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
 * Helper to fetch an article item in the tree view.
 * We need to use "xpath" as a simple "querySelector" does not support finding
 * elements by their contained text.
 * 
 * @param {String} name 
 * @returns 
 */
const findArticleNodeNyName = (name) => {
    return document.evaluate(
        `//li[contains(@class, "o_article")][contains(., "${name}")]`,
        document
    ).iterateNext();
};

/**
 * Simple use case:
 * 
 * No specific "active article".
 * Check that on the root sub-tree, we only show 50 articles.
 * Then load more and verify we now have 100.
 * Etc. until everything is displayed.
 */
const LOAD_MORE_SIMPLE_STEPS = [{
    // check first article is displayed
    trigger: getNthArticleSelector(1, 0),
    run: () => {},
}, {
    // check 50th article is displayed
    trigger: getNthArticleSelector(50, 0),
    run: () => {},
}, {
    // check that the 51th article is NOT displayed, a bit tricky
    trigger: 'ul.o_tree_workspace',
    run: () => {
        const article51 = findArticleNodeNyName("Root Article 50");
        if (!article51) {
            document.querySelector('ul.o_tree_workspace').classList.add(
                'knowledge_load_more_tour_step_root_51_success');
        }
    }
}, {
    // check our previous step succeeded
    trigger: 'ul.o_tree_workspace.knowledge_load_more_tour_step_root_51_success',
    run: () => {},
}, {
    // click to load more articles
    trigger: 'ul.o_tree_workspace .o_knowledge_article_load_more',
}, {
    // check 51th article is displayed
    trigger: getNthArticleSelector(51, 0),
    run: () => {},
}, {
    // check 100th article is displayed
    trigger: getNthArticleSelector(100, 0),
    run: () => {},
}, {
    // check that the 101th article is NOT displayed, a bit tricky
    trigger: 'ul.o_tree_workspace',
    run: () => {
        const article101 = findArticleNodeNyName("Root Article 100");
        if (!article101) {
            document.querySelector('ul.o_tree_workspace').classList.add(
                'knowledge_load_more_tour_step_root_101_success');
        }
    }
}, {
    // check our previous step succeeded
    trigger: 'ul.o_tree_workspace.knowledge_load_more_tour_step_root_101_success',
    run: () => {},
}, {
    // check that there is only a single "load more" button
    trigger: 'ul.o_tree_workspace',
    run: () => {
        const loadMoreButtons = document.querySelectorAll(
            'ul.o_tree_workspace .o_knowledge_article_load_more');
        if (loadMoreButtons.length === 1) {
            document.querySelector('ul.o_tree_workspace').classList.add(
                'knowledge_load_more_tour_step_single_button_success');
        }
    }
}, {
    // check our previous step succeeded
    trigger: 'ul.o_tree_workspace.knowledge_load_more_tour_step_single_button_success',
    run: () => {},
}, {
    // click to load more articles
    trigger: 'ul.o_tree_workspace .o_knowledge_article_load_more',
}, {
    // check 101th article is displayed
    trigger: getNthArticleSelector(101, 0),
    run: () => {},
}, {
    // check 150th article is displayed
    trigger: getNthArticleSelector(150, 0),
    run: () => {},
}, {
    // click to load more articles
    trigger: 'ul.o_tree_workspace .o_knowledge_article_load_more',
}, {
    // check 153th article is displayed (last article of this sub-tree)
    trigger: getNthArticleSelector(153, 0),
    run: () => {},
}, {
    // check that we hide "load more" as we loaded everything in that sub-tree
    trigger: 'ul.o_tree_workspace',
    run: () => {
        const loadMoreButtons = document.querySelectorAll(
            'ul.o_tree_workspace .o_knowledge_article_load_more');
        if (loadMoreButtons.length === 0) {
            document.querySelector('ul.o_tree_workspace').classList.add(
                'knowledge_load_more_tour_step_no_button_success');
        }
    }
}, {
    // check our previous step succeeded
    trigger: 'ul.o_tree_workspace.knowledge_load_more_tour_step_no_button_success',
    run: () => {},
}];

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
 * - 153 root articles
 * - 254 children, all of which are children of "Root Article 103" (the 104th root article)
 * - 344 grand-children, all of which are children of "Child Article 203" (the 204th child article)
 * 
 * When opening the tree, "Root Article 103", "Child Article 203" and "Grand-Child Article 218"
 * should all be forcefully displayed, even though outside of 50 first articles of their respective
 * sub-tree.
 */
const LOAD_MORE_ADVANCED_STEPS = [{
    trigger: 'input.knowledge_search_bar',
    run: 'text Grand-Child Article 218',
}, {
    trigger: 'ul.o_search_tree .o_article a',
}, {
    // check first article is displayed
    trigger: getNthArticleSelector(1, 0),
    run: () => {},
}, {
    // check first article ancestor is displayed (even though outside of 50 first)
    // it should be placed after the 50th article and after the load more
    trigger: `${getNthArticleSelector(50, 0)}+.o_knowledge_article_load_more+${getNthArticleSelector(104, 0)}`,
    run: () => {},
}, {
    // check second article ancestor is displayed (even though outside of 50 first)
    // it should be placed after the 50th child article and after the load more
    trigger: `${getNthArticleSelector(50, 1)}+.o_knowledge_article_load_more+${getNthArticleSelector(204, 1)}`,
    run: () => {},
}, {
    // check the active article is displayed (even though outside of 50 first)
    // it should be placed after the 50th grand-child article and after the load more
    trigger: `${getNthArticleSelector(50, 2)}+.o_knowledge_article_load_more+${getNthArticleSelector(219, 2)}`,
    run: () => {},
}, {
    // click on load more for the root articles
    trigger: `${getNthArticleSelector(50, 0)}+.o_knowledge_article_load_more`,
}, {
    // check first article ancestor is displayed (even though outside of 100 first)
    // it should be placed after 100th root article and after the load more
    trigger: `${getNthArticleSelector(100, 0)}+.o_knowledge_article_load_more+${getNthArticleSelector(104, 0)}`,
    run: () => {},
}, {
    // click on load more for the root articles
    trigger: `${getNthArticleSelector(100, 0)}+.o_knowledge_article_load_more`,
}, {
    // check first article ancestor is displayed at its correct spot
    trigger: `${getNthArticleSelector(103, 0)}+${getNthArticleSelector(104, 0)}`,
    run: () => {},
}, {
    // click on load more for the children articles
    trigger: `${getNthArticleSelector(50, 1)}+.o_knowledge_article_load_more`,
}, {
    // check second article ancestor is displayed (even though outside of 100 first)
    // it should be placed after the 100th child article and after the load more
    trigger: `${getNthArticleSelector(100, 1)}+.o_knowledge_article_load_more+${getNthArticleSelector(204, 1)}`,
    run: () => {},
}, {
    // click on load more for the children articles
    trigger: `${getNthArticleSelector(100, 1)}+.o_knowledge_article_load_more`,
}, {
    // check second article ancestor is displayed (even though outside of 100 first)
    // it should be placed after the 150th child article and after the load more
    trigger: `${getNthArticleSelector(150, 1)}+.o_knowledge_article_load_more+${getNthArticleSelector(204, 1)}`,
    run: () => {},
}, {
    // click on load more for the children articles
    trigger: `${getNthArticleSelector(150, 1)}+.o_knowledge_article_load_more`,
}, {
    // check second article ancestor is displayed (even though outside of 100 first)
    // it should be placed after the 200th child article and after the load more
    trigger: `${getNthArticleSelector(200, 1)}+.o_knowledge_article_load_more+${getNthArticleSelector(204, 1)}`,
    run: () => {},
}, {
    // click on load more for the children articles
    trigger: `${getNthArticleSelector(200, 1)}+.o_knowledge_article_load_more`,
}, {
    // check second article ancestor is displayed (even though outside of 100 first)
    // it should be placed at its correct spot after 203
    trigger: `${getNthArticleSelector(203, 1)}+${getNthArticleSelector(204, 1)}`,
    run: () => {},
}, {
    // click on load more for the grand-children articles
    trigger: `${getNthArticleSelector(50, 2)}+.o_knowledge_article_load_more`,
}, {
    // check active article is displayed (even though outside of 100 first)
    // it should be placed after the 100th grand-child article and after the load more
    trigger: `${getNthArticleSelector(100, 2)}+.o_knowledge_article_load_more+${getNthArticleSelector(219, 2)}`,
    run: () => {},
}, {
    // click on load more for the grand-children articles
    trigger: `${getNthArticleSelector(100, 2)}+.o_knowledge_article_load_more`,
}, {
    // check active article is displayed (even though outside of 100 first)
    // it should be placed after the 150th grand-child article and after the load more
    trigger: `${getNthArticleSelector(150, 2)}+.o_knowledge_article_load_more+${getNthArticleSelector(219, 2)}`,
    run: () => {},
}, {
    // click on load more for the grand-children articles
    trigger: `${getNthArticleSelector(150, 2)}+.o_knowledge_article_load_more`,
}, {
    // check active article is displayed (even though outside of 100 first)
    // it should be placed after the 200th grand-child article and after the load more
    trigger: `${getNthArticleSelector(200, 2)}+.o_knowledge_article_load_more+${getNthArticleSelector(219, 2)}`,
    run: () => {},
}, {
    // click on load more for the grand-children articles
    trigger: `${getNthArticleSelector(200, 2)}+.o_knowledge_article_load_more`,
}, {
    // check active article is displayed (even though outside of 100 first)
    // it should be placed at its correct spot after 218
    trigger: `${getNthArticleSelector(218, 2)}+${getNthArticleSelector(219, 2)}`,
    run: () => {},
}];

registry.category("web_tour.tours").add('website_knowledge_load_more_tour', {
    test: true,
    steps: () => [
        ...LOAD_MORE_SIMPLE_STEPS,
        ...LOAD_MORE_ADVANCED_STEPS,
    ]
});
