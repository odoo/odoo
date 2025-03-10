import { registry } from "@web/core/registry";

/**
 * This tour test that a log note isn't considered
 * as a course review. And also that a member can
 * add only one review.
 */
registry.category("web_tour.tours").add("course_reviews", {
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
            trigger:
                "#chatterRoot:shadow .o-mail-Chatter-content:not(:has(.o-mail-Message-content))",
        },
        {
            // If it fails here, it means the log note is considered as a review
            trigger: "#ratingComposerRoot:shadow span:contains(Add Review)",
            run: "click",
        },
        {
            trigger: "#ratingComposerRoot:shadow .o-mail-Composer-input",
            run: "edit Great course!",
        },
        {
            trigger: "#ratingComposerRoot:shadow .o-mail-Composer-send:enabled",
            run: "click",
        },
        {
            trigger: "a[id=review-tab]",
            run: "click",
        },
        {
            // If it fails here, it means the system is allowing you to add another review.
            trigger: "#ratingComposerRoot:shadow span:contains(Edit Review)",
            run: "click",
        },

        {
            trigger: "#ratingComposerRoot:shadow .o-mail-Composer-input",
            run: function() {
                if (this.anchor.value !== "Great course!") {
                    throw new Error("Composer should contain previous message body.");
                }
            },
        },
    ],
});
