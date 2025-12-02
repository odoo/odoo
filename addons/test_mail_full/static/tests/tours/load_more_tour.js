import { registry } from "@web/core/registry";
import { contains } from "@web/../tests/utils";

registry.category("web_tour.tours").add("load_more_tour", {
    steps: () => [
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread .o-mail-Message",
            run: async function () {
                await contains(".o-mail-Thread .o-mail-Message", {
                    count: 30,
                    target: document.querySelector("#chatterRoot").shadowRoot,
                });
            },
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread button:contains(Load More):not(:visible)",
        },
    ],
});
