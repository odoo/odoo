import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("product_review_highlight_tour", {
    steps: () => [
        {
            trigger: "#o_product_page_reviews_content.show",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message.o-highlighted:has(:text(Test Message))"
        },
    ],
});
