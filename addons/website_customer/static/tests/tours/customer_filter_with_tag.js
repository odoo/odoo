import { clickOnElement, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";
import { queryAll } from "@odoo/hoot-dom";


registerWebsitePreviewTour("customer_filter_with_tag_tour", {
    url: "/customers",
}, () => [
    clickOnElement("tag B", ":iframe .card-body .o_customer_tag:contains('Tag B')"),
    {
        trigger: ":iframe .customer_row",
        run() {
            const cards = queryAll(".customer_card", { root: this.anchor });
            if (!cards.length) {
                console.error("Expected at least one customer card");
            }
        },
    },
    clickOnElement("tag B again", ":iframe .card-body .o_customer_tag:contains('Tag B')"),
    {
        trigger: ":iframe .customer_row",
        run() { if (!queryAll(".customer_card",{ root: this.anchor }).length >= 1)
            console.error("There should be at least 2 customers");
        },
    },
    clickOnElement("tag B from general tags", ":iframe .customer_tags_common:contains('Tag B')"),
    {
        trigger: ":iframe .customer_row",
        run() {
            const cards = queryAll(".customer_card", { root: this.anchor });
            if (!cards.length) {
                console.error("Expected at least one customer card");
            }
        },
    },
    clickOnElement("tag B again", ":iframe .card-body .o_customer_tag:contains('Tag B')"),
    {
        trigger: ":iframe .customer_row",
        run() { if (!queryAll(".customer_card",{ root: this.anchor }).length >= 1)
            console.error("There should be at least 2 customers");
        },
    },
]);
