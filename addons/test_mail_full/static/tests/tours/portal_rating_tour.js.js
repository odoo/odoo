import { registry } from "@web/core/registry";

const ratingCardSelector = ".o_website_rating_card_container";

registry.category("web_tour.tours").add("portal_rating_tour", {
    steps: () => [
        {
            // Ensure that the rating data has been fetched before making a negative assertion for rating cards.
            trigger: "#chatterRoot:shadow .o-mail-Message-body:text(Message without rating)",
        },
        {
            trigger: `#chatterRoot:shadow .o-mail-Chatter-top:not(:has(${ratingCardSelector}))`,
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Composer-input",
            run: "edit Excellent service!",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Composer-send:enabled",
            run: "click",
        },
        {
            trigger: `#chatterRoot:shadow .o-mail-Chatter-top ${ratingCardSelector} .o_website_rating_table_row[data-star='4']:has(:text(100%))`,
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
