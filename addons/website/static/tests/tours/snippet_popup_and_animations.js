import {
    changeOption,
    clickOnEditAndWaitEditMode,
    clickOnElement,
    clickOnSave,
    insertSnippet,
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
    {
        id: "s_three_columns",
        name: "Columns",
        groupName: "Columns",
    },
];

const setOnScrollAnim = function () {
    return [
        changeOption("WebsiteAnimate", 'we-select[data-is-animation-type-selection="true"] we-toggler'),
        changeOption("WebsiteAnimate", 'we-button[data-animation-mode="onScroll"]'),
        changeOption("WebsiteAnimate", 'we-select[data-name="animation_effect_opt"] we-toggler'),
        changeOption("WebsiteAnimate", 'we-button[data-name="o_anim_slide_in_opt"]'),
    ];
};

registerWebsitePreviewTour("snippet_popup_and_animations", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet(snippets[1]), // Media List
    ...insertSnippet(snippets[1]), // Media List
    ...insertSnippet(snippets[2]), // Columns
    clickOnElement("3rd columns", ":iframe .s_three_columns .row > :last-child"),
    ...setOnScrollAnim(),
    {
        content: "Open the Cookies Bar.",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry",
        run: "click",
    },
    {
        trigger: ":iframe #website_cookies_bar:not(.d-none):not(:visible)",
    },
    {
        content: "Scroll to top",
        trigger: ":iframe html",
        run() {
            const animatedColumnEl = this.anchor.querySelector(".s_three_columns .row > :last-child");
            // When the animated element is fully visible, its animation delay
            // should be rounded to -1 in the following condition.
            if (Math.round(parseFloat(animatedColumnEl.style.animationDelay)) !== -1) {
                throw new Error("The scroll animation in the page did not start properly with the cookies bar open.");
            }
            this.anchor.scrollTo({
                top: 0,
                left: 0,
                behavior: 'smooth'
            });
        },
    },
    {
        trigger: ":iframe header#top:not(.o_header_affixed)",
    },
    {
        content: "Wait for the page to be scrolled to the top.",
        trigger: ":iframe .s_three_columns .row > :last-child:not(.o_animating)",
        run() {
            // If the column has been animated successfully, the animation delay
            // should be set to approximately zero when it is not visible.
            // The main goal of the following condition is to verify if the
            // animation delay is being updated as expected.
            if (Math.round(parseFloat(this.anchor.style.animationDelay)) !== 0) {
                throw new Error("The scroll animation in the page did not end properly with the cookies bar open.");
            }
        },
    },
    {
        content: "Close the Cookies Bar.",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry",
        run: "click",
    },
    ...insertSnippet(snippets[0]), // Popup
    ...insertSnippet(snippets[1]), // Media List
    {
        trigger: ".o_website_preview.editor_enable.editor_has_snippets",
    },
    {
        content: "Drag the Columns snippet group and drop it at the bottom of the popup.",
        trigger: '#oe_snippets .oe_snippet[name="Columns"] .oe_snippet_thumbnail:not(.o_we_ongoing_insertion)',
        run: "drag_and_drop :iframe #wrap .s_popup .modal-content.oe_structure .oe_drop_zone:last",
    },
    {
        content: "Click on the s_three_columns snippet.",
        trigger: ':iframe .o_snippet_preview_wrap[data-snippet-id="s_three_columns"]',
        run: "click",
    },
    clickOnElement("3rd columns", ":iframe .s_popup .s_three_columns .row > :last-child"),
    ...setOnScrollAnim(),
    {
        content: "Verify the animation delay of the animated element in the popup at the beginning",
        trigger: ":iframe .s_popup .modal",
        run() {
            const animatedColumnEl = this.anchor.querySelector(".s_three_columns .row > :last-child");
            // When the animated element is fully visible, its animation delay
            // should be rounded to -1 in the following condition.
            if (Math.round(parseFloat(animatedColumnEl.style.animationDelay)) !== -1) {
                throw new Error("The scroll animation in the modal did not start properly.");
            }
            this.anchor.closest(".modal").scrollTo({
                top: 0,
                left: 0,
                behavior: 'smooth'
            });
        },
    },
    {
        content: "Wait until the column is no longer animated/visible.",
        trigger: ":iframe .s_popup .s_three_columns .row > :last-child:not(:has(.o_animating))",
        async run() {
            //TODO: understand why we now wait 500ms before check the condition
            await new Promise((r) => setTimeout(r, 500));
            // If the column has been animated successfully, the animation delay
            // should be set to approximately zero when it is not visible.
            if (Math.round(parseFloat(this.anchor.style.animationDelay)) !== 0) {
                throw new Error("The scroll animation in the modal did not end properly.");
            }
        },
    },
    {
        content: "Close the Popup",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Popup') i.fa-eye",
        run: "click",
    },
    {
        content: "Check that the popup has been closed",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Popup') i.fa-eye-slash",
    },
    clickOnElement("Last image of the 'Columns' snippet", ":iframe .s_three_columns .o_animate_on_scroll img"),
    changeOption("WebsiteAnimate", 'we-toggler:contains("None")'),
    changeOption("WebsiteAnimate", 'we-button[data-animation-mode="onHover"]'),
    {
        trigger: ".snippet-option-WebsiteAnimate we-row:contains('Animation') we-select[data-is-animation-type-selection] we-toggler:contains('On Hover')",
    },
    {
        content: "Check that the hover effect animation has been applied on the image",
        trigger: ":iframe .s_three_columns .o_animate_on_scroll img[data-hover-effect='overlay']",
    },
    ...clickOnSave(),
    ...clickOnEditAndWaitEditMode(),
    clickOnElement("Image of the 'Columns' snippet with the overlay effect", ":iframe .s_three_columns .o_animate_on_scroll img[data-hover-effect='overlay']:not(:visible)"),
    changeOption("WebsiteAnimate", 'we-toggler:contains("Overlay")'),
    changeOption("WebsiteAnimate", 'we-button[data-select-data-attribute="outline"]'),
    {
        trigger: ".snippet-option-WebsiteAnimate we-select[data-attribute-name='hoverEffect'] we-toggler:contains('Outline')",
    },
    {
        content: "Check that the outline effect has been applied on the image",
        trigger: ":iframe .s_three_columns .o_animate_on_scroll img[data-hover-effect='outline']:not(:visible)",
    },
    ...clickOnSave(),
    {
        content: "Check that the image src is not the raw data",
        trigger: ":iframe .s_three_columns .o_animate_on_scroll img[data-hover-effect='outline']:not(:visible)",
        run() {
            const imgEl = document.querySelector("iframe").contentDocument.querySelector(".s_three_columns .o_animate_on_scroll img[data-hover-effect='outline']");
            const src = imgEl.getAttribute("src");
            if (src.startsWith("data:image")) {
                throw new Error("The image source should not be raw data after the editor save");
            }
        },
    },
    ...clickOnEditAndWaitEditMode(),
    clickOnElement("Image of the 'Columns' snippet with the outline effect", ":iframe .s_three_columns .o_animate_on_scroll img[data-hover-effect='outline']:not(:visible)"),
    changeOption("ImageTools", 'we-select:contains("Filter") we-toggler:contains("None")'),
    changeOption("ImageTools", 'we-button:contains("Blur")'),
    {
        trigger: ".snippet-option-ImageTools we-select:contains('Filter') we-toggler:contains('Blur')",
    },
    {
        content: "Check that the Blur filter has been applied on the image",
        trigger: ":iframe .s_three_columns .o_animate_on_scroll img[data-gl-filter='blur']:not(:visible)",
    },
    {
        content: "Click on the 'undo' button",
        trigger: ".o_we_external_history_buttons button.fa-undo",
        run: "click",
    },
    {
        content: "Check that the Blur filter has been removed from the image",
        trigger: ":iframe .s_three_columns .o_animate_on_scroll img:not([data-gl-filter='blur']):not(:visible)",
    },
    ...clickOnSave(),
    {
        content: "Check that the image src is not the raw data",
        trigger: ":iframe .s_three_columns .o_animate_on_scroll img[data-hover-effect='outline']:not(:visible)",
        run() {
            const imgEl = document.querySelector("iframe").contentDocument.querySelector(".s_three_columns .o_animate_on_scroll img[data-hover-effect='outline']");
            const src = imgEl.getAttribute("src");
            if (src.startsWith("data:image")) {
                throw new Error("The image source should not be raw data after the editor save");
            }
        },
    },
]);
