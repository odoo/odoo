/** @odoo-module */

import wTourUtils from "@website/js/tours/tour_utils";

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
        content: `Check that the #wrapwrap ${hasScrollbar ? "has" : "does not have"} a vertical scrollbar.`,
        trigger: `:iframe ${hasScrollbar ? "body:not(.modal-open)" : "body.modal-open"}`,
        run: function () {
            const wrapwrapEl = this.anchor.querySelector("#wrapwrap");
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
    ...wTourUtils.dragNDrop(snippets[1]), // Media List
    ...wTourUtils.dragNDrop(snippets[0]), // Popup
    checkScrollbar(false),
    {
        content: 'Click on the s_popup snippet',
        in_modal: false,
        trigger: ':iframe .s_popup .modal',
        run: "click",
    },
    toggleBackdrop(), // hide Popup backdrop
    checkScrollbar(true),
    wTourUtils.goBackToBlocks(),
    {
        content: "Drag the Content snippet group and drop it at the bottom of the popup.",
        trigger: '#oe_snippets .oe_snippet[name="Content"] .oe_snippet_thumbnail:not(.o_we_already_dragging)',
        run: "drag_and_drop :iframe #wrap .s_popup .oe_drop_zone:last",
    },
    {
        content: "Click on the s_media_list snippet.",
        trigger: ':iframe .o_snippet_preview_wrap[data-snippet-id="s_media_list"]',
        run: "click",
    },
    checkScrollbar(false),
    {
        content: "Select the Media List snippet in the Popup.",
        trigger: ":iframe #wrap .s_popup .modal-content .s_media_list",
        run: "click",
    },
    {
        content: "Remove the Media List snippet in the Popup.",
        trigger: ":iframe .oe_overlay.oe_active .oe_snippet_remove",
        run: "click",
    },
    checkScrollbar(true),
    toggleBackdrop(), // show Popup backdrop
    checkScrollbar(false),
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
    toggleBackdrop(), // show Cookies Bar backdrop
    checkScrollbar(false),
    toggleBackdrop(), // hide Cookies Bar backdrop
    checkScrollbar(true),
    {
        content: "Open the Popup that has backdrop.",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:first",
        run: "click",
    },
    checkScrollbar(false),
    wTourUtils.goBackToBlocks(),
    {
        content: "Drag the Content snippet group and drop it at the bottom of the popup.",
        trigger: '#oe_snippets .oe_snippet[name="Content"] .oe_snippet_thumbnail:not(.o_we_already_dragging)',
        run: "drag_and_drop :iframe #wrap .s_popup .oe_drop_zone:last",
    },
    {
        content: "Click on the s_media_list snippet.",
        trigger: ':iframe .o_snippet_preview_wrap[data-snippet-id="s_media_list"]',
        run: "click",
    },
    checkScrollbar(true), //the popup backdrop is activated so there should have a scrollbar on #wrapwrap
    {
        content: 'Click on the s_popup snippet',
        in_modal: false,
        trigger: ':iframe .s_popup .modal',
        run: "click",
    },
    {
        content: "Remove the s_popup snippet",
        trigger: ".o_we_customize_panel we-customizeblock-options:contains('Popup') we-button.oe_snippet_remove:first",
        in_modal: false,
        async run(helpers) {
            helpers.click();
            // TODO: remove the below setTimeout. Without it, goBackToBlocks() not works.
            await new Promise((r) => setTimeout(r, 1000));
        }
    },
    checkScrollbar(true),
    wTourUtils.goBackToBlocks(),
    {
        content: "Drag the Content snippet group and drop it in the Cookies Bar.",
        trigger: '#oe_snippets .oe_snippet[name="Content"] .oe_snippet_thumbnail:not(.o_we_already_dragging)',
        run: "drag_and_drop :iframe #website_cookies_bar .modal-content.oe_structure",
    },
    {
        content: "Click on the s_media_list snippet.",
        trigger: ':iframe .o_snippet_preview_wrap[data-snippet-id="s_media_list"]',
        run: "click",
    },
    {
        content: "Select the Media List snippet in the Cookies Bar.",
        trigger: ":iframe #website_cookies_bar .modal-content .s_media_list",
        run: "click",
    },
    {
        content: "Duplicate the Media List snippet",
        trigger: ".o_we_customize_panel we-customizeblock-options:contains('Media List') we-button.oe_snippet_clone:first",
        run() {
            // TODO: use run: "click", instead
            this.anchor.click();
        }
    },
    checkScrollbar(false),
    {
        content: "Remove the first Media List snippet in the Cookies Bar.",
        trigger: ":iframe .oe_overlay.oe_active .oe_snippet_remove",
        run: "click",
    },
    {
        content: "Remove the second Media List snippet in the Cookies Bar.",
        trigger: ":iframe .oe_overlay.oe_active .oe_snippet_remove",
        run: "click",
    },
    checkScrollbar(true),
]);
