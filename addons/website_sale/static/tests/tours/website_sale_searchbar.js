// import { registry } from "@web/core/registry";
import {
    changeOption,
    changeOptionInPopover,
    clickOnElement,
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

function makeAndCheckSearch(word, color = null) {
    return [
        {
            trigger: ":iframe input.search-query",
            run: `edit ${word}`,
        },
        {
            trigger: `:iframe span.text-primary-emphasis:contains(${word})`,
        },
    ];
}

registerWebsitePreviewTour(
    "test_searchbar_search_functionality",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_searchbar_input",
            name: "Search",
        }),
        clickOnElement("Searchbar", ":iframe .s_searchbar_input[data-snippet='s_searchbar_input']"),
        ...changeOptionInPopover("Search", "Search within", "Products"),
        changeOption(
            "Search",
            "[data-label='Description'] [data-action-id='setNonEmptyDataAttribute']"
        ),
        {
            trigger:
                ":iframe .o_search_result_item .o_search_result_item_detail:not(:contains(Description))",
        },
        ...clickOnSave(),
        {
            trigger: ":iframe input.search-query",
            run: `edit red`,
        },
        {
            trigger: `:iframe .color_preview`,
            run(helper) {
                if (helper.anchor.style.backgroundColor !== "rgb(255, 0, 0)") {
                    throw new Error("Error in previewing color");
                }
            },
        },
        ...makeAndCheckSearch("200"),
        ...makeAndCheckSearch("111111111"),
        ...makeAndCheckSearch("BMW"),
        ...makeAndCheckSearch("Mercedes"),
        ...makeAndCheckSearch("Hundai"),
    ]
);
