import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("portal_rating_tour", {
    steps: () => [
        {
            trigger: "#chatterRoot:shadow :not(:has(.o_website_rating_card_container))",
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
            trigger: "#chatterRoot:shadow .o_website_rating_card_container",
        },
        {
            trigger: "#chatterRoot:shadow .o_website_rating_table_row[data-star='4']:contains(100%)",
        },
        
    ],
});
