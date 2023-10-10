/** @odoo-module */

import wTourUtils from "@website/js/tours/tour_utils";

const snippets = [
    {
        id: "s_popup",
        name: "Popup",
    },
    {
        id: "s_media_list",
        name: "Media List",
    },
];

const checkScrollbar = function (hasScrollbar) {
    return {
        content: `Check that the #wrapwrap ${hasScrollbar ? "has" : "does not have"} a vertical scrollbar.`,
        trigger: `iframe ${hasScrollbar ? "body:not(.modal-open)" : "body.modal-open"}`,
        run: function () {
            const wrapwrapEl = this.$anchor[0].querySelector("#wrapwrap");
            const wrapwrapStyle = window.getComputedStyle(wrapwrapEl);
            if (!hasScrollbar && (wrapwrapStyle.overflow !== "hidden" || parseFloat(wrapwrapStyle.paddingRight) < 1)) {
                console.error("error The #wrapwrap vertical scrollbar should be hidden");
            } else if (hasScrollbar && (wrapwrapStyle.overflow === "hidden" || parseFloat(wrapwrapStyle.paddingRight) > 0)) {
                console.error("error The #wrapwrap vertical scrollbar should be displayed");
            }
        },
    };
};

const toggleBackdrop = function () {
    return wTourUtils.changeOption('SnippetPopup', 'we-button[data-name="popup_backdrop_opt"] we-checkbox', 'backdrop');
};

wTourUtils.registerWebsitePreviewTour("snippet_popup_and_scrollbar", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    wTourUtils.dragNDrop(snippets[1]), // Media List
    wTourUtils.dragNDrop(snippets[0]), // Popup
    checkScrollbar(false),
    {
        content: 'Click on the s_popup snippet',
        in_modal: false,
        trigger: 'iframe .s_popup .modal',
    },
    toggleBackdrop(), // hide Popup backdrop
    checkScrollbar(true),
    wTourUtils.goBackToBlocks(),
    {
        content: "Drag the Media List block and drop it in the popup.",
        trigger: "#oe_snippets .oe_snippet:has(> [data-snippet='s_media_list']) .oe_snippet_thumbnail",
        run: "drag_and_drop_native iframe #wrap .s_popup .modal-content.oe_structure",
    },
    checkScrollbar(false),
    {
        content: "Select the Media List snippet in the Popup.",
        trigger: "iframe #wrap .s_popup .modal-content .s_media_list",
    },
    {
        content: "Remove the Media List snippet in the Popup.",
        trigger: "iframe .oe_overlay.oe_active .oe_snippet_remove",
    },
    checkScrollbar(true),
    toggleBackdrop(), // show Popup backdrop
    checkScrollbar(false),
    {
        content: "Close the Popup.",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry",
    },
    checkScrollbar(true),
    {
        content: "Open the Cookies Bar.",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:last-child",
    },
    checkScrollbar(true),
    toggleBackdrop(), // show Cookies Bar backdrop
    checkScrollbar(false),
    toggleBackdrop(), // hide Cookies Bar backdrop
    checkScrollbar(true),
    {
        content: "Open the Popup.",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry",
    },
    checkScrollbar(false),
    wTourUtils.goBackToBlocks(),
    {
        content: "Drag the Media List block and drop it in the popup.",
        trigger: "#oe_snippets .oe_snippet:has(> [data-snippet='s_media_list']) .oe_snippet_thumbnail",
        run: "drag_and_drop_native iframe #wrap .s_popup .modal-content.oe_structure",
    },
    checkScrollbar(false),
    {
        content: 'Click on the s_popup snippet',
        in_modal: false,
        trigger: 'iframe .s_popup .modal',
    },
    {
        content: "Remove the s_popup snippet",
        trigger: ".o_we_customize_panel we-customizeblock-options:contains('Popup') we-button.oe_snippet_remove:first",
        in_modal: false,
        run: "click",
    },
    checkScrollbar(true),
    wTourUtils.goBackToBlocks(),
    {
        content: "Drag a Media List snippet and drop it in the Cookies Bar.",
        trigger: "#oe_snippets .oe_snippet:has(> [data-snippet='s_media_list']) .oe_snippet_thumbnail",
        run: "drag_and_drop_native iframe #website_cookies_bar .modal-content.oe_structure",
    },
    {
        content: "Select the Media List snippet in the Cookies Bar.",
        trigger: "iframe #website_cookies_bar .modal-content .s_media_list",
    },
    {
        content: "Duplicate the Media List snippet",
        trigger: ".o_we_customize_panel we-customizeblock-options:contains('Media List') we-button.oe_snippet_clone:first",
        in_modal: false,
        run: "click",
    },
    checkScrollbar(false),
    {
        content: "Remove the first Media List snippet in the Cookies Bar.",
        trigger: "iframe .oe_overlay.oe_active .oe_snippet_remove",
    },
    {
        content: "Remove the second Media List snippet in the Cookies Bar.",
        trigger: "iframe .oe_overlay.oe_active .oe_snippet_remove",
    },
    checkScrollbar(true),
]);
