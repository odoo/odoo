import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("load_more_tour", {
    steps: () => [
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread:has(.o-mail-Message, 30)",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread button:contains(Load More):not(:visible)",
        },
    ],
});
