import {
    registerWebsitePreviewTour,
    insertSnippet,
    changeOption,
    clickOnElement,
    changeOptionInPopover,
    clickOnSnippet,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "snippet_store_locator",
    {
        edition: true,
        url: "/",
    },
    () => [
        ...insertSnippet({
            id: "s_store_locator",
            name: "Store Locator",
            groupName: "Social",
        }),
        {
            content: "Check that the 'List Is Empty' message is displayed",
            trigger: ":iframe div.alert",
        },
        ...clickOnSnippet(".s_store_locator"),
        changeOption("Store Locator", ".o_select_menu .dropdown-toggle"),
        clickOnElement(`the partner entry`, "[data-choice-index='0']"),
        {
            content: "Check that the map is now rendered",
            trigger: ":iframe section.o_location_selector_view",
        },
        {
            content: "Check that the details textarea is displayed",
            trigger: ":iframe div.o_location_selector_textarea",
        },
        {
            content: "Check that no toltip is displayed",
            trigger: ":iframe body:not(:has(section.o_location_selector_view div.leaflet-tooltip))",
        },
        {
            content: "Check that the map contains OpenStreetMaps tiles",
            trigger: ":iframe div.leaflet-tile-container img[src*='tile.openstreetmap.org']",
        },
        changeOption("Store Locator", "[data-label='Phone Number'] input"),
        {
            content: "Check that the phone number is displayed",
            trigger: ":iframe div.o_location_selector_textarea i.fa-phone",
        },
        changeOption("Store Locator", "[data-label='Email'] input"),
        {
            content: "Check that the email address is displayed",
            trigger: ":iframe div.o_location_selector_textarea i.fa-envelope",
        },
        ...changeOptionInPopover("Store Locator", "Details", "[title='Tooltip']"),
        {
            content: "Check that the tooltip is displayed",
            trigger: ":iframe section.o_location_selector_view div.leaflet-tooltip",
        },
        {
            content: "Check that the details textarea is removed",
            trigger: ":iframe body:not(:has(div.o_location_selector_textarea i.fa-envelope))",
        },
    ]
);
