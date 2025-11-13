import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("load_more_tour", {
    steps: () => [
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread .o-mail-Message:count(30)",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread button:contains(Load More):not(:visible)",
        },
    ],
});
