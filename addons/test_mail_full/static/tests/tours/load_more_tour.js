import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("load_more_tour", {
    steps: () => [
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread .o-mail-Message:count(30)",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread button:contains(Load More)",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread .o-mail-Message:count(31)",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread:not(:has(button:contains(Load More)))",
        },
    ],
});
