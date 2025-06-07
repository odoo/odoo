/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * This tour test that a log note isn't considered
 * as a course review. And also that a member can
 * add only one review and react to them.
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
            trigger: "span:contains(Add Review)",
            run: "click",
        },
        {
            trigger: ".modal.modal_shown.show div.o_portal_chatter_composer_body textarea",
            run: "edit Great course!",
        },
        {
            trigger: ".modal.modal_shown.show button.o_portal_chatter_composer_btn",
            run: "click",
        },
        {
            trigger: ".o_wslides_course_header_nav_review",
            run() {
                const a = document.querySelector("a[id=review-tab]");
                if (a.textContent !== "Reviews (1)") {
                    throw Error("Text should be 'Reviews (1)'.");
                }
                a.click();
            },
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message-textContent:contains(Great course!)",
        },
        {
            // If it fails here, it means the system is allowing you to add another review.
            trigger: "span:contains(Edit Review)",
            run: "click",
        },
        {
            trigger: "div.o_portal_chatter_composer_body textarea:value(Great course!)",
            run: "edit Mid course!",
        },
        {
            trigger: ".modal.modal_shown.show button.o_portal_chatter_composer_btn",
            run() {
                if (this.anchor.textContent !== "Update review") {
                    throw Error("Button text should be 'Update review'.");
                }
                this.anchor.click();
            },
        },
        {
            content: "Reload page (fetch message)",
            trigger: "#chatterRoot:shadow .o-mail-Chatter",
            run() {
                location.reload();
            },
        },
        {
            trigger: "a[id=review-tab]",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message-textContent:contains(Mid course!)",
            run: "hover && click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message [title='Add a Reaction']",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-Emoji[data-codepoints='😃']",
            run: "click",
        },
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message .o-mail-MessageReactions-add:not(:visible)",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message .o-mail-MessageReaction",
            run: "click",
        },
        { trigger: '#chatterRoot:shadow .o-mail-Message button:contains("Comment")', run: "click" },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message .o-mail-Composer textarea",
            run: "edit Thanks for enjoying my 'mid' course, you mid student",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message .o-mail-Composer textarea",
            run: "press Enter",
        },
        {
            trigger: `#chatterRoot:shadow .o_wrating_publisher_comment:contains("Thanks for enjoying my 'mid' course, you mid student")`,
        },
    ],
});
