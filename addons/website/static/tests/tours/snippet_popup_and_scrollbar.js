/** @odoo-module */

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

const toggleBackdrop = function () {
    return changeOption('SnippetPopup', 'we-button[data-name="popup_backdrop_opt"] we-checkbox', 'backdrop');
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
    toggleBackdrop(), // hide Popup backdrop
    checkScrollbar(true),
    goBackToBlocks(),
    {
        content: "Drag the Content snippet group and drop it at the bottom of the popup.",
        trigger: '#oe_snippets .oe_snippet[name="Content"] .oe_snippet_thumbnail:not(.o_we_ongoing_insertion)',
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
    /* task-4185877
    checkScrollbar(false),
    */
    goBackToBlocks(),
    {
        content: "Drag the Content snippet group and drop it at the bottom of the popup.",
        trigger: '#oe_snippets .oe_snippet[name="Content"] .oe_snippet_thumbnail:not(.o_we_ongoing_insertion)',
        run: "drag_and_drop :iframe #wrap .s_popup .oe_drop_zone:last",
    },
    {
        content: "Click on the s_media_list snippet.",
        trigger: ':iframe .o_snippet_preview_wrap[data-snippet-id="s_media_list"]',
        run: "click",
    },
    /* task-4185877
    checkScrollbar(true), // The popup backdrop is activated so there should be a scrollbar
    */
    {
        content: 'Click on the s_popup snippet',
        trigger: ':iframe .s_popup .modal',
        run: "click",
    },
    {
        content: "Remove the s_popup snippet",
        trigger: ".o_we_customize_panel we-customizeblock-options:contains('Popup') we-button.oe_snippet_remove:first",
        async run(helpers) {
            await helpers.click();
            // TODO: remove the below setTimeout. Without it, goBackToBlocks() not works.
            await new Promise((r) => setTimeout(r, 1000));
        }
    },
    checkScrollbar(true),
    goBackToBlocks(),
    {
        content: "Drag the Content snippet group and drop it in the Cookies Bar.",
        trigger: '#oe_snippets .oe_snippet[name="Content"] .oe_snippet_thumbnail:not(.o_we_ongoing_insertion)',
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
