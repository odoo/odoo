import { queryAll } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";

registry
    .category("web_tour.tours")
    .add("website_sale_product_reviews_has_only_ratings", {
        steps: () => [
            {
                trigger: ".o_product_page_reviews_title",
                run: "click",
            },
            {
                content: "The review is present in the rating section",
                trigger: "#chatterRoot:shadow .o-mail-Message-textContent:contains(Review)",
            },
            {
                content: "Check that the review is the only message displayed",
                trigger: "#chatterRoot:shadow .o-mail-Message",
                run: () => {
                    const messages = queryAll("#chatterRoot:shadow .o-mail-Message");
                    if (messages.length !== 1) {
                        throw new Error(
                            `Expected exactly 1 message in the reviews section, found ${messages.length}`
                        );
                    }
                    if (!messages[0].textContent.includes("Review")) {
                        throw new Error("The displayed message is not the review");
                    }
                },
            },
        ],
    });
