/** @odoo-module */

import {
    dragAndDropArticle,
    endKnowledgeTour,
} from "@knowledge/../tests/tours/knowledge_tour_utils";
import { registry } from "@web/core/registry";

// Checks that one can add an readonly article to its favorites

registry.category("web_tour.tours").add("knowledge_readonly_favorite_tour", {
    steps: () => [
        {
            trigger: ".o_article_active:contains(Readonly Article 1)",
        },
        {
            // Make sure we are on the readonly article 1, that is not favorited, and
            // click on the toggle favorite button.
            trigger: "a.o_knowledge_toggle_favorite:has(.fa-star-o)",
            run: "click",
        },
        {
            trigger: "a.o_knowledge_toggle_favorite:has(.fa-star)",
        },
        {
            // Check that the article has been added to the favorites
            trigger: 'section[data-section="favorites"]:contains("Readonly Article 1")',
        },
        {
            // Open the other readonly article
            trigger: '.o_knowledge_sidebar .o_article_name:contains("Readonly Article 2")',
            run: "click",
        },
        {
            trigger: ".o_article_active:contains(Readonly Article 2)",
        },
        {
            // Make sure we are on the readonly article 1, that is not favorited, and
            // click on the toggle favorite button.
            trigger: "a.o_knowledge_toggle_favorite:has(.fa-star-o)",
            run: "click",
        },
        {
            // Check that the article has been added to the favorites under the other
            // one and try to resquence the favorite articles
            trigger: 'section[data-section="favorites"] li:last:contains("Readonly Article 2")',
            run: () =>
                dragAndDropArticle(
                    'section[data-section="favorites"] li:last .o_article_handle',
                    'section[data-section="favorites"] li:first .o_article_handle'
                ),
        },
        {
            trigger: 'section[data-section="favorites"] li:first:contains("Readonly Article 2")',
        },
        {
            // Check that articles have been reordered correctly
            trigger: 'section[data-section="favorites"] li:last:contains("Readonly Article 1")',
        },
        ...endKnowledgeTour(),
    ],
});
