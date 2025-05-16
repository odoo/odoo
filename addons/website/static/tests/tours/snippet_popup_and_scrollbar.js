import {
    changeOption,
    insertSnippet,
    goBackToBlocks,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const snippets = [
    {
        id: "s_popup",
        name: "Popup",
        groupName: "Content",
    },
    {
        id: "s_media_list",
        name: "Media List",
        groupName: "Content",
    },
];

const checkScrollbar = function (hasScrollbar) {
    return {
        content: `Check that the page ${hasScrollbar ? "has" : "does not have"} a vertical scrollbar.`,
        trigger: `:iframe ${hasScrollbar ? "body:not(.modal-open)" : "body.modal-open"}`,
        run: function () {
            const style = window.getComputedStyle(this.anchor);
            if (!hasScrollbar && (style.overflow !== "hidden" || parseFloat(style.paddingRight) < 1)) {
                console.error("error The vertical scrollbar should be hidden");
            } else if (hasScrollbar && (style.overflow === "hidden" || parseFloat(style.paddingRight) > 0)) {
                console.error("error The vertical scrollbar should be displayed");
            }
        },
    };
};

function toggleBackdrop(snippet) {
    return changeOption(`${snippet}`, "[data-action-id='setBackdrop'] .form-check-input");
};

registerWebsitePreviewTour("snippet_popup_and_scrollbar", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet(snippets[1]), // Media List
    ...insertSnippet(snippets[0]), // Popup
    checkScrollbar(false),
    {
        content: 'Click on the s_popup snippet',
        trigger: ':iframe .s_popup .modal',
        run: "click",
    },
    toggleBackdrop("Popup"), // hide Popup backdrop
    checkScrollbar(true),
    goBackToBlocks(),
    {
        content: "Drag the Content snippet group and drop it at the bottom of the popup.",
        trigger: ".o-snippets-menu .o_block_tab:not(.o_we_ongoing_insertion) .o_snippet[name='Content'].o_draggable .o_snippet_thumbnail",
        run: "drag_and_drop :iframe #wrap .s_popup .oe_drop_zone:last",
    },
    {
        content: "Click on the s_media_list snippet.",
        trigger: ":iframe .o_add_snippets_preview [data-snippet='s_media_list']",
        run: "click",
    },
    checkScrollbar(false),
    {
        trigger: ":iframe:not(:has(.o_loading_screen))",
    },
    {
        content: "Select the Media List snippet in the Popup.",
        trigger: ":iframe .s_popup .s_media_list",
        run: "click",
    },
    {
        content: "Remove the s_media_list snippet",
        trigger: ".overlay .o_overlay_options .oe_snippet_remove",
        run: "click",
    },
    checkScrollbar(true),
    toggleBackdrop("Popup"), // show Popup backdrop
    {
        content: "Close the Popup that has now backdrop.",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:first",
        run: "click",
    },
    checkScrollbar(true),
    {
        content: "Open the Cookies Bar.",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:last",
        run: "click",
    },
    checkScrollbar(true),
    toggleBackdrop("Cookies Bar"), // show Cookies Bar backdrop
    toggleBackdrop("Cookies Bar"), // hide Cookies Bar backdrop
    checkScrollbar(true),
    {
        content: "Open the Popup that has backdrop.",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:first",
        run: "click",
    },
    goBackToBlocks(),
    {
        content: "Drag the Content snippet group and drop it at the bottom of the popup.",
        trigger: ".o-snippets-menu .o_snippet[name='Content'] .o_snippet_thumbnail:not(.o_we_ongoing_insertion)",
        run: "drag_and_drop :iframe #wrap .s_popup .modal-content.oe_structure .oe_drop_zone:last",
    },
    {
        content: "Click on the s_media_list snippet.",
        trigger: ":iframe .o_add_snippets_preview [data-snippet='s_media_list']",
        run: "click",
    },
    {
        content: 'Click on the s_popup snippet',
        trigger: ':iframe .s_popup .modal',
        run() {
            this.anchor.scrollIntoView();
            this.anchor.click();
        },
    },
    {
        content: "Remove the s_popup snippet",
        trigger: ".overlay .o_overlay_options .oe_snippet_remove",
        run: "click",
    },
    checkScrollbar(true),
    {
        content: "Open the Cookie Bar.",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry",
        run: "click",
    },
    goBackToBlocks(),
    {
        content: "Drag the Content snippet group and drop it in the Cookies Bar.",
        trigger: ".o-snippets-menu .o_snippet[name='Content'] .o_snippet_thumbnail:not(.o_we_ongoing_insertion)",
        run: "drag_and_drop :iframe #website_cookies_bar .modal-content.oe_structure",
    },
    {
        content: "Click on the s_media_list snippet.",
        trigger: ":iframe .o_add_snippets_preview [data-snippet='s_media_list']",
        run: "click",
    },
    {
        trigger: ":iframe:not(:has(.o_loading_screen))",
    },
    {
        content: "Select the Media List snippet in the Cookies Bar.",
        trigger: ":iframe #website_cookies_bar .modal-content .s_media_list",
        run: "click",
    },
    {
        content: "Duplicate the Media List snippet",
        trigger: ".o_customize_tab .options-container[data-container-title='Media List'] .oe_snippet_clone",
        run: "click",
    },
    checkScrollbar(false),
    {
        content: "Select the Media List snippet in the Cookies Bar.",
        trigger: ":iframe #website_cookies_bar .modal-content .s_media_list",
        run: "click",
    },
    {
        content: "Remove the first Media List snippet in the Cookies Bar.",
        trigger: ".overlay .o_overlay_options .oe_snippet_remove",
        run: "click",
    },
    {
        content: "Remove the second Media List snippet in the Cookies Bar.",
        trigger: ".overlay .o_overlay_options .oe_snippet_remove",
        run: "click",
    },
    checkScrollbar(true),
]);
