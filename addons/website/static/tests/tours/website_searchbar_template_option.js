import { clickOnSnippet, insertSnippet, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";


registerWebsitePreviewTour('website_sale_searchbar_template_option', {
    url: `/`,
    edition: true,
}, () => [
    ...insertSnippet({
    id: "s_searchbar_input",
    name: "Search",
    }),
    ...clickOnSnippet({id: "s_searchbar_input", name: "Search"}),
    {
        content: "Select template option",
        trigger: ".o_customize_tab [data-container-title='Search'] button[id='template_opt'",
        run: "click"
    },
    {
        content: "Check default template id",
        trigger: ":iframe input[type='search'][data-template-id='website.s_searchbar.autocomplete']"
    },
    {
        content: "Select second template option",
        trigger: "div[data-action-value='website.s_searchbar.autocomplete_second']",
        run: "click"
    },
    {
        content: "Check second template id",
        trigger: ":iframe input[type='search'][data-template-id='website.s_searchbar.autocomplete_second']"
    },

])