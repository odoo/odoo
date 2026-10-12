import { registry } from "@web/core/registry";

const ratingCardSelector = ".o_website_rating_card_container";

registry.category("web_tour.tours").add("portal_rating_tour", {
    steps: () => [
        {
            // Ensure that the rating data has been fetched before making a negative assertion for rating cards.
            trigger: "#chatterRoot:shadow .o-mail-Message-body:text(Message without rating)",
        },
        {
            trigger: `#chatterRoot:shadow .o-mail-Chatter-top ${ratingCardSelector} .text-muted:text(0 reviews)`,
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Chatter-top .btn:contains(Write a review)",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o_review_composer_modal .o-mail-Composer-input",
            run: "edit Excellent service!",
        },
        {
            trigger: "#chatterRoot:shadow .o_review_composer_modal .o-mail-Composer-send:enabled",
            run: "click",
        },
        {
            trigger: `#chatterRoot:shadow .o-mail-Chatter-top ${ratingCardSelector} .o_website_rating_table_row[data-star='4'] .o_rating_progressbar`,
        },
    ],
});

registry.category("web_tour.tours").add("portal_display_rating_tour", {
    steps: () => [
        {
            trigger: `#chatterRoot:shadow .o-mail-Chatter-top ${ratingCardSelector}`,
        },
    ],
});

registry.category("web_tour.tours").add("portal_not_display_rating_tour", {
    steps: () => [
        {
            // Ensure that the rating data has been fetched before making a negative assertion for rating cards.
            trigger: "#chatterRoot:shadow .o-mail-Message-body:text(Message with rating)",
        },
        {
            trigger: `#chatterRoot:shadow .o-mail-Chatter-top:not(:has(${ratingCardSelector}))`,
        },
    ],
});
