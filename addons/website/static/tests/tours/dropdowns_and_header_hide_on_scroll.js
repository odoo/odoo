/** @odoo-module */

import {
    clickOnSave,
    changeOption,
    checkIfVisibleOnScreen,
    insertSnippet,
    registerWebsitePreviewTour,
    selectHeader,
} from "@website/js/tours/tour_utils";

const checkIfUserMenuNotMasked = function () {
    return [
        {
            content: "Click on the user dropdown",
            trigger: ":iframe #wrapwrap header li.dropdown > a:contains(mitchell admin)",
            run: "click",
        },
        checkIfVisibleOnScreen(
            ":iframe #wrapwrap header li.dropdown .dropdown-menu.show a[href='/my/home']"
        ),
    ];
};

const scrollDownToMediaList = function () {
    return {
        content: "Scroll down the page a little to leave the dropdown partially visible",
        trigger: ":iframe #wrapwrap .s_media_list",
        run() {
            // Scroll down to the media list snippet.
            this.anchor.scrollIntoView({ behavior: "instant" });
        },
    };
};

registerWebsitePreviewTour("dropdowns_and_header_hide_on_scroll", {
    test: true,
    url: "/",
    edition: true,
    checkDelay: 100,
}, () => [
    ...insertSnippet({id: "s_media_list", name: "Media List", groupName: "Content"}),
    selectHeader(),
    changeOption("undefined", 'we-select[data-variable="header-scroll-effect"]'),
    changeOption("undefined", 'we-button[data-name="header_effect_fixed_opt"]'),
    {
        trigger: ":iframe #wrapwrap header.o_header_fixed",
    },
    selectHeader(),
    changeOption("WebsiteLevelColor", 'we-select[data-variable="header-template"] we-toggler'),
    changeOption("WebsiteLevelColor", 'we-button[data-name="header_sales_two_opt"]'),
    {
        content: "check that header_sales_two_opt is well selected before save",
        trigger: ":iframe #wrapwrap header.o_header_fixed div[aria-label=Middle] div[role=search]",
        timeout: 30000,
    },
    ...clickOnSave(undefined, 30000),
    ...checkIfUserMenuNotMasked(),
    // We scroll the page a little because when clicking on the dropdown, the
    // page needs to scroll to the top first and then open the dropdown menu.
    scrollDownToMediaList(),
    ...checkIfUserMenuNotMasked(),
    // We scroll the page again because when typing in the searchbar input, the
    // page needs also to scroll to the top first and then open the dropdown
    // with the search results.
    scrollDownToMediaList(),
    {
        content: "Type a search query into the searchbar input",
        trigger: ":iframe #wrapwrap header .s_searchbar_input input.search-query",
        run: "edit a",
    },
    checkIfVisibleOnScreen(":iframe #wrapwrap header .s_searchbar_input.show .o_dropdown_menu.show"),
]);
