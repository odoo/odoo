import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("portal_rating_pagination_tour", {
    steps: () => [
        {
            trigger: "#chatterRoot:shadow .o-mail-Message-body:text(Fourth review)",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread .o-mail-Message:count(3)",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread button:contains(Load More)",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message-body:text(Five star review)",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread .o-mail-Message:count(4)",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread:not(:has(button:contains(Load More)))",
        },
        {
            trigger: "#chatterRoot:shadow .o_website_rating_table_row[data-star='5']",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread .o-mail-Message:count(1)",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message-body:text(Five star review)",
        },
        {
            trigger: "#chatterRoot:shadow .o_website_rating_table_row[data-star='5']",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread .o-mail-Message:count(3)",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread button:contains(Load More)",
        },
    ],
});
