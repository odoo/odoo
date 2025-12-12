import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("slides_review_highlight_tour", {
    steps: () => [
        {
            trigger: "a[id=review-tab].active",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message.o-highlighted:has(:text(Test Message))",
        },
    ],
});
