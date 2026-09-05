import {
    registerWebsitePreviewTour,
    insertSnippet,
    changeOption,
    clickOnElement,
    changeOptionInPopover,
    clickOnSnippet,
} from "@website/js/tours/tour_utils";
import { delay } from "@web/core/utils/concurrency";

const assertLocationCount = (count) => [
    {
        content: "Check the number of locations listed in the option",
        trigger: "div[data-container-title='Store Locator'] .o_we_table_wrapper table",
        async run() {
            await delay(100);
            const els = document.querySelectorAll(
                "div[data-container-title='Store Locator'] .o_we_table_wrapper table tr"
            );
            if (els.length != count) {
                throw new Error("Wrong count of locations listed in the option");
            }
        },
    },
    {
        content: "Check the number of locations listed in the snippet",
        trigger: ":iframe  .s_store_locator",
        run() {
            const els = document
                .querySelector("iframe")
                .contentDocument.querySelectorAll("#o_location_selector_list_view button");
            if (els.length != count) {
                throw new Error("Wrong number of locations listed in the snippet");
            }
        },
    },
];

registerWebsitePreviewTour(
    "snippet_store_locator",
    {
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_store_locator",
            name: "Store Locator",
            groupName: "Social",
        }),
        ...clickOnSnippet(".s_store_locator"),
        ...assertLocationCount(2),
        {
            content: "Check that the map is now rendered",
            trigger: ":iframe section.o_location_selector_view",
        },
        {
            content: "Check that the details textarea is displayed",
            trigger: ":iframe div.o_location_selector_textarea",
        },
        {
            content: "Check that no tooltip is displayed",
            trigger: ":iframe body:not(:has(section.o_location_selector_view div.leaflet-tooltip))",
        },
        {
            content: "Check that the map contains OpenStreetMaps tiles",
            trigger: ":iframe div.leaflet-tile-container img[src*='tile.openstreetmap.org']",
        },
        changeOption("Store Locator", "[data-label='Phone Number'] input"),
        {
            content: "Check that the phone number is displayed",
            trigger: ":iframe div.o_location_selector_textarea i[data-icon='phone']",
        },
        changeOption("Store Locator", "[data-label='Email'] input"),
        {
            content: "Check that the email address is displayed",
            trigger: ":iframe div.o_location_selector_textarea i[data-icon='mail']",
        },
        changeOption("Store Locator", "[data-label='Website'] input"),
        {
            content: "Check that the website is displayed",
            trigger: ":iframe div.o_location_selector_textarea i[data-icon='link']",
        },
        ...changeOptionInPopover("Store Locator", "Details", "Tooltip"),
        {
            content: "Check that the tooltip is displayed",
            trigger: ":iframe section.o_location_selector_view div.leaflet-tooltip",
        },
        {
            content: "Check that the details textarea is removed",
            trigger: ":iframe body:not(:has(div.o_location_selector_textarea i.fa-envelope))",
        },
        changeOption("Store Locator", ".o_select_menu .dropdown-toggle"),
        clickOnElement(`partner entry`, "[data-choice-index='0']"),
        ...assertLocationCount(3),
        clickOnElement(`remove button`, "button.builder_list_remove_item"),
        ...assertLocationCount(2),
        clickOnElement(`remove button`, "button.builder_list_remove_item"),
        ...assertLocationCount(1),
        clickOnElement(`remove button`, "button.builder_list_remove_item"),
        ...assertLocationCount(0),
        {
            content: "Check that the 'List Is Empty' message is displayed",
            trigger: ":iframe .s_store_locator div[role='dialog']",
        },
    ]
);
