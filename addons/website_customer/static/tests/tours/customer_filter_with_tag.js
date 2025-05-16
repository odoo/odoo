import { registry } from "@web/core/registry";

function clickonElementWithPageReload(elementName, selector) {
    return {
        content: `Clicking on the ${elementName}`,
        trigger: selector,
        run: "click",
        expectUnloadPage: true,
    };
}
function checkNumberOfCustomerCards(numberOfCards) {
    return {
        content: `Checking number of cards to be ${numberOfCards}`,
        trigger: ".customer_row",
        run({ queryAll }) {
            const cards = queryAll(".customer_card", { root: this.anchor });
            if (cards.length !== numberOfCards) {
                console.error(`Expected ${numberOfCards} customer card(s)`);
            }
        },
    };
}
registry.category("web_tour.tours").add("customer_filter_with_tag_tour", {
    url: "/customers",
    steps: () => [
        clickonElementWithPageReload("tag A", ".card-body .o_customer_tag:contains('Tag A')"),
        {
            content: "Check if Tag A appears as an applied filter in the UI.",
            trigger: ".o_filter_tag:contains(Tag A)",
        },
        checkNumberOfCustomerCards(1),
        clickonElementWithPageReload("tag A again", ".card-body .o_customer_tag:contains('Tag A')"),
        checkNumberOfCustomerCards(2),
        clickonElementWithPageReload(
            "tag A from general tags",
            ".customer_tags_common:contains('Tag A')"
        ),
        {
            content: "Check if Tag A appears as an applied filter in the UI.",
            trigger: ".o_filter_tag:contains(Tag A)",
        },
        checkNumberOfCustomerCards(1),
        clickonElementWithPageReload("tag B", ".card-body .o_customer_tag:contains('Tag B')"),
        {
            content: "Check if Tag B appears as an applied filter in the UI.",
            trigger: ".o_filter_tag:contains(Tag B)",
        },
        {
            content: "Check if the url is changed with query string `?tag`",
            trigger: "body",
            run() {
                if (!window.location.href.includes("?tag")) {
                    console.error("The url should contain the query string `?tag`");
                }
            },
        },
        checkNumberOfCustomerCards(2),
        {
            trigger: "input.search-query",
            run: "edit Company A",
        },
        {
            trigger: "button.oe_search_button",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Check if the url is changed with query string `?search`",
            trigger: "body",
            run() {
                if (!window.location.href.includes("?search")) {
                    console.error("The url should contain the query string `?search`");
                }
            },
        },
        checkNumberOfCustomerCards(1),
    ],
});
