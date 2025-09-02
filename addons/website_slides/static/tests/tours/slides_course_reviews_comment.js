import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("course_reviews_comment", {
    url: "/slides",
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
            trigger: "#chatterRoot:shadow .o-mail-Message button:contains('comment')",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message .o-mail-Composer-input",
            run: "edit Putting a comment...",
        },
        // When the comment box is closed, the content of the composer is preserved
        {
            trigger: "#chatterRoot:shadow .o-mail-Message button:contains('comment')",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message:not(:has(.o-mail-Composer-input))",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message button:contains('comment')",
            run: "click",
        },
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message .o-mail-Composer-input:value('Putting a comment...')",
        },
        // Send the comment
        {
            trigger: "#chatterRoot:shadow .o-mail-Message button:contains('save')",
            run: "click",
        },
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message:contains('Putting a comment...') :not(:has(button:contains('comment')))",
        },
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message:contains(Putting a comment...) .o_wrating_publisher_comment .o-dropdown",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-dropdown-item:contains(Edit)",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message .o-mail-Composer-input",
            run: "edit Editing the comment...",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message button:contains(save)",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message:contains(Editing the comment...)",
        },
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message:contains(Editing the comment...) .o_wrating_publisher_comment .o-dropdown",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-dropdown-item:contains(Delete)",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message:not(:contains(Editing the comment...)",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message button:contains(comment)",
            run: "click",
        },
    ],
});
