/** @odoo-module */

import {
    clickOnEditAndWaitEditMode,
    clickOnElement,
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
    changeOptionInPopover,
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
        ...changeOptionInPopover("Card", "Animation", "On Scroll"),
        ...changeOptionInPopover("Card", "Effect", "Slide"),
    ];
};

function scrollToSnippet(snippetId) {
    return [
        {
            trigger: `:iframe .${snippetId}`,
            content: `Scroll to the ${snippetId} snippet`,
            run() {
                this.anchor.scrollIntoView();
            },
        },
    ];
}

registerWebsitePreviewTour(
    "snippet_popup_and_animations",
    {
        url: "/",
        edition: true,
    },
    () => [
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
                const animatedColumnEl = this.anchor.querySelector(
                    ".s_three_columns .row > :last-child"
                );
                // When the animated element is fully visible, its animation
                // delay should be rounded to -1 in the following condition.
                if (Math.round(parseFloat(animatedColumnEl.style.animationDelay)) !== -1) {
                    throw new Error(
                        "The scroll animation in the page did not start properly with the cookies bar open."
                    );
                }
                this.anchor.scrollTo({
                    top: 0,
                    left: 0,
                    behavior: "smooth",
                });
            },
        },
        {
            trigger: ":iframe header#top:not(.o_header_affixed)",
        },
        {
            content: "Wait for the page to be scrolled to the top.",
            trigger: ":iframe .s_three_columns .row > .o_animating:last-child",
            isActive: [`:iframe .s_three_columns .row > .o_animating:last-child`],
            async run({ waitUntil, anchor }) {
                await waitUntil(() => !anchor.classList.contains(`o_animating`), {
                    timeout: 10000,
                });
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
            content: "Drag the Columns snippet group and drop it at the bottom of the popup.",
            trigger:
                ".o-snippets-menu .o_block_tab:not(.o_we_ongoing_insertion) .o_snippet[name='Columns'].o_draggable .o_snippet_thumbnail",
            run: "drag_and_drop :iframe #wrap .s_popup .modal-content.oe_structure .oe_drop_zone:last",
        },
        {
            content: "Click on the s_three_columns snippet.",
            trigger: ":iframe .o_add_snippets_preview [data-snippet-id='s_three_columns']",
            run: "click",
        },
        {
            trigger: ":iframe:not(:has(.o_loading_screen))",
        },
        clickOnElement("3rd columns", ":iframe .s_popup .s_three_columns .row > :last-child"),
        ...setOnScrollAnim(),
        {
            content:
                "Verify the animation delay of the animated element in the popup at the beginning",
            trigger: ":iframe .s_popup .modal",
            run() {
                const animatedColumnEl = this.anchor.querySelector(
                    ".s_three_columns .row > :last-child"
                );
                // When the animated element is fully visible, its animation
                // delay should be rounded to -1 in the following condition.
                if (Math.round(parseFloat(animatedColumnEl.style.animationDelay)) !== -1) {
                    throw new Error("The scroll animation in the modal did not start properly.");
                }
                this.anchor.closest(".modal").scrollTo({
                    top: 0,
                    left: 0,
                    behavior: "smooth",
                });
            },
        },
        {
            content: "Wait until the column is no longer animated/visible.",
            trigger: ":iframe .s_three_columns .row > .o_animating:last-child",
            isActive: [`:iframe .s_three_columns .row > .o_animating:last-child`],
            async run({ anchor, waitUntil }) {
                await waitUntil(() => !anchor.classList.contains(`o_animating`), {
                    timeout: 10000,
                });
            },
        },
        {
            content: "Close the Popup",
            trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Popup') i.fa-eye",
            run: "click",
        },
        {
            content: "Check that the popup has been closed",
            trigger: ":iframe [data-snippet=s_popup] > .modal:not(:visible)",
        },
        ...scrollToSnippet("s_three_columns"),
        clickOnElement(
            "Last image of the 'Columns' snippet",
            ":iframe .s_three_columns .o_animate_on_scroll img"
        ),
        ...changeOptionInPopover("Image", "Animation", "On Hover"),
        {
            content: "Check that the hover effect animation has been applied on the image",
            trigger:
                ":iframe .s_three_columns .o_animate_on_scroll img[data-hover-effect='overlay']",
        },
        ...clickOnSave(),
        ...clickOnEditAndWaitEditMode(),
        ...scrollToSnippet("s_three_columns"),
        clickOnElement(
            "Image of the 'Columns' snippet with the overlay effect",
            ":iframe .s_three_columns .o_animate_on_scroll img[data-hover-effect='overlay']"
        ),
        ...changeOptionInPopover("Image", "Effect", "Outline"),
        {
            trigger:
                ".o_customize_tab .options-container[data-container-title='Image'] [data-label='Effect'] button:contains('Outline')",
        },
        {
            content: "Check that the outline effect has been applied on the image",
            trigger:
                ":iframe .s_three_columns .o_animate_on_scroll img[data-hover-effect='outline']",
        },
        ...clickOnSave(),
        {
            content: "Check that the image src is not the raw data",
            trigger:
                ":iframe .s_three_columns .o_animate_on_scroll img[data-hover-effect='outline']",
            run() {
                const imgEl = document
                    .querySelector("iframe")
                    .contentDocument.querySelector(
                        ".s_three_columns .o_animate_on_scroll img[data-hover-effect='outline']"
                    );
                const src = imgEl.getAttribute("src");
                if (src.startsWith("data:image")) {
                    throw new Error(
                        "The image source should not be raw data after the editor save"
                    );
                }
            },
        },
        ...clickOnEditAndWaitEditMode(),
        ...scrollToSnippet("s_three_columns"),
        clickOnElement(
            "Image of the 'Columns' snippet with the outline effect",
            ":iframe .s_three_columns .o_animate_on_scroll img[data-hover-effect='outline']"
        ),
        ...changeOptionInPopover("Image", "Filter", "Blur"),
        {
            trigger:
                ".o_customize_tab .options-container[data-container-title='Image'] [data-label='Filter'] button:contains('Blur')",
        },
        {
            content: "Check that the Blur filter has been applied on the image",
            trigger: ":iframe .s_three_columns .o_animate_on_scroll img[data-gl-filter='blur']",
        },
        {
            content: "Click on the 'undo' button",
            trigger: ".o-snippets-top-actions button.fa-undo",
            run: "click",
        },
        {
            content: "Check that the Blur filter has been removed from the image",
            trigger:
                ":iframe .s_three_columns .o_animate_on_scroll img:not([data-gl-filter='blur'])",
        },
        ...clickOnSave(),
        {
            content: "Check that the image src is not the raw data",
            trigger:
                ":iframe .s_three_columns .o_animate_on_scroll img[data-hover-effect='outline']",
            run() {
                const imgEl = document
                    .querySelector("iframe")
                    .contentDocument.querySelector(
                        ".s_three_columns .o_animate_on_scroll img[data-hover-effect='outline']"
                    );
                const src = imgEl.getAttribute("src");
                if (src.startsWith("data:image")) {
                    throw new Error(
                        "The image source should not be raw data after the editor save"
                    );
                }
            },
        },
    ]
);
