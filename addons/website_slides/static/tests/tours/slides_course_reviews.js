import { registry } from "@web/core/registry";
import slidesTourTools from "@website_slides/../tests/tours/slides_tour_tools";

/**
 * This tour test that a log note isn't considered
 * as a course review. And also that a member can
 * add only one review and react to them.
 */
registry.category("web_tour.tours").add("course_reviews", {
    steps: () => [
        {
            trigger: "a:contains(Basics of Gardening - Test)",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: "a[id=review-tab]",
            run: "click",
        },
        {
            // If it fails here, it means that the portal chatter has fetched the notes.
            trigger: "#chatterRoot:shadow .o-mail-Chatter:has(:text(No messages yet.))",
        },
        {
            // If it fails here, it means the log note is considered as a review
            content: "Add your review",
            trigger: ".o_rating_popup_composer_btn",
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
            trigger: "body:not(:has(.modal.show))",
        },
        {
            trigger: ".o_wslides_course_header_nav_review",
        },
        {
            trigger: "a[id=review-tab]:contains('Reviews (1)')",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message-textContent:contains(Great course!)",
        },
        {
            // If it fails here, it means the system is allowing you to add another review.
            content: "The button to add your review is hidden.",
            trigger: ".o_rating_popup_composer_btn:not(:visible)",
        },
        ...slidesTourTools.openMessageAction("Great course!", "edit"),
        {
            trigger: "div.o_portal_chatter_composer_body textarea:value(Great course!)",
            run: "edit Mid course!",
        },
        {
            trigger:
                ".modal.modal_shown.show button.o_portal_chatter_composer_btn:contains(update review)",
            run: "click",
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
            trigger:
                "#chatterRoot:shadow .o-mail-QuickReactionMenu-emoji span:contains('👍'):not(:visible)",
            run: "click",
        },
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message .o-mail-MessageReactions:not([title='Add a Reaction'])",
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
            run: "press ctrl+Enter",
        },
        {
            trigger: `#chatterRoot:shadow .o_wrating_publisher_comment:contains("Thanks for enjoying my 'mid' course, you mid student")`,
        },
    ],
});
