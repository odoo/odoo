import {
    changeOption,
    changeOptionInPopover,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "website_searchbar_template_option",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_searchbar_input",
            name: "Search",
        }),
        {
            content: "Check default template id",
            trigger:
                ":iframe input[type='search'][data-template-id='website.s_searchbar.autocomplete']",
        },
        ...clickOnSnippet({ id: "s_searchbar_input", name: "Search" }),
        ...changeOptionInPopover("Search", "Search within", "Everything"),
        {
            content: "Limit search to 'Knowledge Articles'",
            trigger: ':iframe .s_searchbar_input[action="/website/search"]',
        },
        changeOption("Search", "[id='template_opt']"),
        {
            trigger: "[data-action-value='website.s_searchbar.autocomplete_second']",
            run: "hover",
        },
        {
            trigger: ":iframe input[data-template-id='website.s_searchbar.autocomplete_second']",
        },
        {
            content: "Select second template option",
            trigger: "div[data-action-value='website.s_searchbar.autocomplete_second']",
            run: "click",
        },
        {
            content: "Check second template id",
            trigger:
                ":iframe input[type='search'][data-template-id='website.s_searchbar.autocomplete_second']",
        },
        changeOption("Search", "[data-action-param='displayDescription']"),
        {
            content: "Check second template id",
            trigger: ":iframe .o_search_result_item:not(:contains(Description))",
        },
        {
            content: "Set placeholder",
            trigger: "[data-action-id='setPlaceholder'] input",
            run: "edit Hello",
        },
        {
            content: "Check placeholder value",
            trigger: ":iframe input[placeholder='Hello']",
        },
    ]
);
