/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * This tour tests that a public user can not react to messages
 */
registry.category("web_tour.tours").add("course_reviews_reaction_public", {
    url: "/slides",
    steps: () => [
        {
            trigger: "a:contains(Basics of Gardening - Test)",
            run: "click",
        },
        {
            trigger: "a[id=review-tab]",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message-textContent:contains(Bad course!)",
            run: "hover && click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message .o-mail-Message-actions",
            run: async () => {
                const addReactionButton = document.querySelector('#chatterRoot').shadowRoot.querySelector("[title='Add a Reaction']")
                if (addReactionButton) {
                    throw new Error("Public user is able to react");
                }
            },
        },
    ],
});
