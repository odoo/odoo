import {
    clickOnSave,
    changeOptionInPopover,
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

registerWebsitePreviewTour(
    "dropdowns_and_header_hide_on_scroll",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_media_list", name: "Media List", groupName: "Content" }),
        selectHeader(),
        ...changeOptionInPopover("Header", "Scroll Effect", ".dropdown-item:contains('Fixed')"),
        {
            content: "Wait for the option to be applied",
            trigger: "[data-label='Scroll Effect'] .dropdown-toggle:contains('Fixed')",
            timeout: 30000,
        },
        {
            trigger: ":iframe #wrapwrap header.o_header_fixed",
        },
        selectHeader(),
        ...changeOptionInPopover(
            "Header",
            "Template",
            ".dropdown-item[data-action-param*=sales_two]"
        ),
        {
            trigger: ":iframe .o_header_sales_two_top",
            timeout: 30000,
        },
        {
            content: "check that header_sales_two_opt is well selected",
            trigger:
                ":iframe #wrapwrap header.o_header_fixed div[aria-label=Middle] div[role=search]",
        },
        ...clickOnSave(undefined, 30000),
        ...checkIfUserMenuNotMasked(),
        // We scroll the page a little because when clicking on the dropdown,
        // the page needs to scroll to the top first and then open the dropdown
        // menu.
        scrollDownToMediaList(),
        ...checkIfUserMenuNotMasked(),
        // We scroll the page again because when typing in the searchbar input,
        // the page needs also to scroll to the top first and then open the
        // dropdown with the search results.
        scrollDownToMediaList(),
        {
            content: "Type a search query into the searchbar input",
            trigger: ":iframe #wrapwrap header .s_searchbar_input input.search-query",
            run: "edit a",
        },
        checkIfVisibleOnScreen(
            ":iframe #wrapwrap header .s_searchbar_input.show .o_dropdown_menu.show"
        ),
    ]
);
