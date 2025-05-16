import { clickOnElement, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";
import { queryAll } from "@odoo/hoot-dom";

registerWebsitePreviewTour(
    "customer_filter_with_tag_tour",
    {
        url: "/customers",
    },
    () => [
        clickOnElement("tag A", ":iframe .card-body .o_customer_tag:contains('Tag A')"),
        {
            trigger: ":iframe .customer_row",
            run() {
                const cards = queryAll(".customer_card", { root: this.anchor });
                if (!cards.length) {
                    console.error("Expected at least one customer card");
                }
            },
        },
        clickOnElement("tag A again", ":iframe .card-body .o_customer_tag:contains('Tag A')"),
        {
            trigger: ":iframe .customer_row",
            run() {
                if (!queryAll(".customer_card", { root: this.anchor }).length >= 1) {
                    console.error("There should be at least 2 customers");
                }
            },
        },
        clickOnElement("tag A from general tags", ":iframe .o_filter_tag:contains('Tag A')"),
        {
            trigger: ":iframe .customer_row",
            run() {
                const cards = queryAll(".customer_card", { root: this.anchor });
                if (!cards.length) {
                    console.error("Expected at least one customer card");
                }
            },
        },
        clickOnElement("tag B", ":iframe .card-body .o_customer_tag:contains('Tag B')"),
        {
            content: "Check if the url is changed with query string `?tag`",
            trigger: "body",
            run() {
                if (!window.location.href.includes("?tag")) {
                    console.error("The url should contain the query string `?tag`");
                }
            },
        },
        {
            trigger: ":iframe .customer_row",
            run() {
                if (!queryAll(".customer_card", { root: this.anchor }).length >= 1) {
                    console.error("There should be at least 2 customers");
                }
            },
        },
    ]
);
