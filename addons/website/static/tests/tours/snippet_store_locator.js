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
            if (els.length !== count) {
                throw new Error("Wrong count of locations listed in the option");
            }
        },
    },
    ...assertLocationCountInSnippet(count),
];

const assertLocationCountInSnippet = (count) => [
    {
        content: "Check the number of locations listed in the snippet",
        trigger: ":iframe  .s_store_locator",
        async run() {
            // The searchbar filtering is debounced
            await delay(350);
            const els = document
                .querySelector("iframe")
                .contentDocument.querySelectorAll("#o_location_selector_list_view button");
            if (els.length !== count) {
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
        ...changeOptionInPopover("Store Locator", "Zoom", "200 m"),
        {
            content: "Check that the zoom level is changed",
            trigger: ":iframe section.s_store_locator[data-map-zoom='15']",
        },
        {
            content: "Change the searchbar placeholder",
            trigger: "[data-label='Placeholder'] input",
            run: "edit newplaceholder && press Tab",
        },
        {
            content: "Check that the searchbar placeholder is changed",
            trigger: ":iframe input#o_location_selector_search[placeholder='newplaceholder']",
        },
        {
            content: "Wait for the options panel to settle",
            trigger: "[data-container-title='Store Locator'] .o_select_menu .dropdown-toggle",
            run: async () => await delay(300),
        },
        changeOption("Store Locator", ".o_select_menu .dropdown-toggle"),
        clickOnElement(`partner entry`, "[data-choice-index='0']"),
        ...assertLocationCount(3),
        changeOption("Store Locator", "[data-label='Image'] input"),
        {
            content: "Select the new location",
            trigger: ":iframe #o_location_selector_list_view button:contains('AAAAA')",
            run: "click",
        },
        {
            content: "Check that the location's image is displayed",
            trigger: ":iframe div.o_location_selector_textarea img[src^='data:image/']",
        },
        {
            content: "Search for the new location",
            trigger: ":iframe input#o_location_selector_search",
            run: "edit Ramillies && press Tab",
        },
        {
            content: "Click on the search button",
            trigger: ":iframe .s_store_locator button[aria-label='Search']",
            run: "click",
        },
        ...assertLocationCountInSnippet(1),
        {
            content: "Clear the search input",
            trigger: ":iframe input#o_location_selector_search",
            async run({ edit }) {
                await edit("");
            },
        },
        {
            content: "Click on the search button again",
            trigger: ":iframe .s_store_locator button[aria-label='Search']",
            run: "click",
        },
        ...assertLocationCountInSnippet(3),
        {
            content: "Move the sidebar to the right",
            trigger:
                "[data-container-title='Store Locator'] [data-label='Sidebar Location'] [title='Right']",
            run: "click",
        },
        {
            content: "Check that the sidebar is now on the right",
            trigger: ":iframe .s_store_locator div.flex-row-reverse #location_selector_list_view",
        },
        changeOption("Store Locator", "[data-label='Hide Offscreen'] input"),
        {
            content: "Check that the snippet height was fixed when hiding offscreen locations",
            trigger: ":iframe section.s_store_locator.o_half_screen_height",
        },
        changeOption("Store Locator", "[data-label='Hide Offscreen'] input"),
        changeOption("Store Locator", "[data-label='Display Sidebar'] input"),
        {
            content: "Check that the sidebar is removed",
            trigger: ":iframe section.s_store_locator:not(:has(#location_selector_list_view))",
        },
        changeOption("Store Locator", "[data-label='Display Sidebar'] input"),
        {
            content: "Check that the sidebar is back",
            trigger: ":iframe section.s_store_locator #location_selector_list_view",
        },
        ...changeOptionInPopover("Store Locator", "Details", "Tooltip"),
        {
            content: "Check that the tooltip is displayed",
            trigger: ":iframe section.o_location_selector_view div.leaflet-tooltip",
        },
        {
            content: "Check that the details textarea is removed",
            trigger: ":iframe section.s_store_locator:not(:has(div.o_location_selector_textarea))",
        },
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
