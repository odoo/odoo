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
    {
        id: "s_three_columns",
        name: "Columns",
    },
];

const setOnScrollAnim = function () {
    return [
        wTourUtils.changeOption("WebsiteAnimate", 'we-select[data-is-animation-type-selection="true"] we-toggler'),
        wTourUtils.changeOption("WebsiteAnimate", 'we-button[data-animation-mode="onScroll"]'),
        wTourUtils.changeOption("WebsiteAnimate", 'we-select[data-name="animation_effect_opt"] we-toggler'),
        wTourUtils.changeOption("WebsiteAnimate", 'we-button[data-name="o_anim_slide_in_opt"]'),
    ];
};

wTourUtils.registerWebsitePreviewTour("snippet_popup_and_animations", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    wTourUtils.dragNDrop(snippets[1]), // Media List
    wTourUtils.dragNDrop(snippets[1]), // Media List
    wTourUtils.dragNDrop(snippets[2]), // Columns
    wTourUtils.clickOnElement("3rd columns", "iframe .s_three_columns .row > :last-child"),
    ...setOnScrollAnim(),
    {
        content: "Open the Cookies Bar.",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry",
    },
    {
        content: "Scroll to top",
        trigger: "iframe #wrapwrap",
        extra_trigger: "iframe #website_cookies_bar:not(.d-none)",
        run: function () {
            const animatedColumnEl = this.$anchor[0].querySelector(".s_three_columns .row > :last-child");
            // When the animated element is fully visible, its animation delay
            // should be rounded to -1 in the following condition.
            if (Math.round(parseFloat(animatedColumnEl.style.animationDelay)) !== -1) {
                console.error("The scroll animation in the page did not start properly with the cookies bar open.");
            }
            this.$anchor[0].scrollTo({
                top: 0,
                left: 0,
                behavior: 'smooth'
            });
        },
    },
    {
        content: "Wait for the page to be scrolled to the top.",
        trigger: "iframe .s_three_columns .row > :last-child:not(.o_animating)",
        extra_trigger: "iframe header#top:not(.o_header_affixed)",
        run: function () {
            // If the column has been animated successfully, the animation delay
            // should be set to approximately zero when it is not visible.
            // The main goal of the following condition is to verify if the
            // animation delay is being updated as expected.
            if (Math.round(parseFloat(this.$anchor[0].style.animationDelay)) !== 0) {
                console.error("The scroll animation in the page did not end properly with the cookies bar open.");
            }
        },
    },
    {
        content: "Close the Cookies Bar.",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry",
        run: "click",
    },
    wTourUtils.dragNDrop(snippets[0]), // Popup
    wTourUtils.dragNDrop(snippets[1]), // Media List
    {
        content: "Drag the Columns building block and drop it at the bottom of the popup.",
        trigger: '#oe_snippets .oe_snippet[name="Columns"] .oe_snippet_thumbnail:not(.o_we_already_dragging)',
        extra_trigger: ".o_website_preview.editor_enable.editor_has_snippets",
        run: "drag_and_drop_native iframe #wrapwrap .modal-content .s_media_list .container > .row > :last-child",
    },
    wTourUtils.clickOnElement("3rd columns", "iframe .s_popup .s_three_columns .row > :last-child"),
    ...setOnScrollAnim(),
    {
        content: "Verify the animation delay of the animated element in the popup at the beginning",
        trigger: "iframe .s_popup .modal",
        run: function () {
            const animatedColumnEl = this.$anchor[0].querySelector(".s_three_columns .row > :last-child");
            // When the animated element is fully visible, its animation delay
            // should be rounded to -1 in the following condition.
            if (Math.round(parseFloat(animatedColumnEl.style.animationDelay)) !== -1) {
                console.error("The scroll animation in the modal did not start properly.");
            }
            this.$anchor[0].closest(".modal").scrollTo({
                top: 0,
                left: 0,
                behavior: 'smooth'
            });
        },
    },
    {
        content: "Wait until the column is no longer animated/visible.",
        trigger: "iframe .s_popup .s_three_columns .row > :last-child:not(.o_animating)",
        run: function () {
            // If the column has been animated successfully, the animation delay
            // should be set to approximately zero when it is not visible.
            if (Math.round(parseFloat(this.$anchor[0].style.animationDelay)) !== 0) {
                console.error("The scroll animation in the modal did not end properly.");
            }
        },
    },
]);
