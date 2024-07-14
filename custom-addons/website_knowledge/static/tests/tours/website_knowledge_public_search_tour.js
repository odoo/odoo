/** @odoo-module */

/**
 * Public user search Knowledge flow tour (for published articles).
 * Features tested:
 * - Check that tree contains all articles
 * - Write search term in search bar
 * - Check that search tree renders the correct matching articles
 * - Clean search bar
 */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('website_knowledge_public_search_tour', {
    test: true,
    steps: () => [{ // Check that section tree contains all articles
    content: "Check that search tree contains 'My Article'",
    trigger: '.o_article_name:contains("My Article")',
    run() {},
}, {
    content: "Unfold 'My Article'", // Unfold because 'My Article' wasn't added to the unfolded articles
    trigger: '.o_article_active .o_article_caret',
}, {
    content: "Check that search tree contains 'Child Article'",
    trigger: '.o_article_name:contains("Child Article")',
    run() {},
}, {
    content: "Check that search tree contains 'Sibling Article'",
    trigger: '.o_article_name:contains("Sibling Article")',
    run() {},
}, { // Write search term in search bar
    content: "Write 'M' in the search bar",
    trigger: '.knowledge_search_bar',
    run: 'text My'
}, {
    content: "Trigger keyup event to start the search",
    trigger: '.knowledge_search_bar',
    run() {
        $('.knowledge_search_bar').trigger($.Event("keyup", { key: "Enter" }));
    },
}, { // Check tree rendering with matching articles
    content: "Check that search tree contains 'My Article'",
    trigger: '.o_article_name:contains("My Article")',
    run() {},
}, {
    content: "Check that search tree doesn't contain 'Child Article'",
    trigger: '.o_knowledge_tree:not(:has(.o_article_name:contains("Child Article")))',
    run() {},
}, {
    content: "Check that search tree doesn't contain 'Sibling Article'",
    trigger: '.o_knowledge_tree:not(:has(.o_article_name:contains("Sibling Article")))',
    run() {},
}, { // Clean search bar
    content: "Clean search bar",
    trigger: '.knowledge_search_bar',
    run: function (action) {
        action.remove_text("", ".knowledge_search_bar");
    },
}]});
