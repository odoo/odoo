import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_sale_product_review_multicompany", {
    steps: () => [
        {
            content: "The other company's portal user's review should be in the chatter",
            trigger: ".o-mail-Message-body:contains(Review)",
        },
        {
            content: "No access error dialog was raised",
            trigger: "body:not(:has(.o_error_dialog))",
        },
        {
            content: "Click send message",
            trigger: ".o-mail-Chatter-sendMessage",
            run: "click",
        },
        {
            content: "There should be a suggested recipient matching the portal user's parsed email",
            trigger: ".o-mail-RecipientsInput:contains(portal_2)",
            run: "click",
        },
    ],
});
