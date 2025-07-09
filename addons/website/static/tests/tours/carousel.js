/** @odoo-module */

import { delay } from "@odoo/hoot-dom";
import {
    insertSnippet,
    clickOnSnippet,
    changeOption,
    clickOnSave,
    registerWebsitePreviewTour,
    goBackToBlocks,
} from "@website/js/tours/tour_utils";

const carouselInnerSelector = ":iframe .carousel-inner";
const ANCHOR_HOVER_BG_COLOR = '#EF6C6C17';

registerWebsitePreviewTour("carousel_content_removal", {
    url: '/',
    edition: true,
}, () => [
    ...insertSnippet({
        id: 's_carousel',
        name: 'Carousel',
        groupName: "Intro",
}), {
    trigger: ":iframe .carousel .carousel-item.active .carousel-content",
    content: "Select the active carousel item.",
    run: "click",
}, {
    trigger: ".overlay .oe_snippet_remove",
    content: "Remove the active carousel item.",
    run: "click",
}, {
    trigger: ":iframe .carousel .carousel-item.active .container:not(:has(*)):not(:visible)",
    content: "Check for a carousel slide with an empty container tag",
},
    goBackToBlocks(),
    ...insertSnippet({
        id: "s_quotes_carousel",
        name: "Blockquote",
        groupName: "People",
}), {
    trigger: ":iframe .s_quotes_carousel_wrapper .carousel-item.active .s_blockquote",
    content: "Select the blockquote.",
    run: "click",
}, {
    trigger: ".overlay .oe_snippet_remove",
    content: "Remove the blockquote from the carousel item.",
    run: "click",
}, {
    trigger: ":iframe .s_quotes_carousel_wrapper .carousel-item.active:not(:has(.s_blockquote))",
    content: "Check that the blockquote has been removed and the carousel item is empty.",
}]);

const checkSlides = (number, position) => {
    const nSlide = (n) => `div.carousel-item:eq(${n})`;
    const hasNSlide = (n) => `:has(${nSlide(n - 1)}):not(:has(${nSlide(n)}))`;
    const activeSlide = (p) => `${nSlide(p - 1)}:is(.active)`;
    return {
        content: `Check if there are ${number} slides and if the ${position} is active`,
        trigger: `${carouselInnerSelector}${hasNSlide(number)} ${activeSlide(position)}`,
        async run() {
            // When continue the tour directly, slide menu can disappears or
            // action can not be done.
            await delay(500);
        },
    };
};

registerWebsitePreviewTour(
    "snippet_carousel",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_carousel", name: "Carousel", groupName: "Intro" }),
        ...clickOnSnippet(".carousel .carousel-item.active"),
        // Slide to the right.
        changeOption("Slide (1/3)", "[aria-label='Move Forward']"),
        checkSlides(3, 2),
        // Add a slide (with the "CarouselItem" option).
        changeOption("Slide (2/3)", "button[aria-label='Add Slide']"),
        checkSlides(4, 3),
        // Remove a slide.
        changeOption("Slide (3/4)", "button[aria-label='Remove Slide']"),
        checkSlides(3, 2),
        {
            trigger: ":iframe .carousel .carousel-control-prev",
            content: "Slide the carousel to the left with the arrows.",
            run: "click",
        },
        checkSlides(3, 1),
        // Add a slide (with the "Carousel" option).
        changeOption("Carousel", "[data-action-id='addSlide']"),
        checkSlides(4, 2),
        {
            content: "Check if the slide indicator was correctly updated",
            trigger: ".options-container span:contains(' (2/4)')",
        },
        // Check if we can still remove a slide.
        changeOption("Slide (2/4)", "button[aria-label='Remove Slide']"),
        checkSlides(3, 1),
        // Slide to the left.
        changeOption("Slide (1/3)", "[aria-label='Move Backward']"),
        checkSlides(3, 3),
        // Reorder the slides and make it the second one.
        changeOption("Slide (3/3)", "[data-action-value='prev']"),
        checkSlides(3, 2),
        ...clickOnSave(),
        // Check that saving always sets the first slide as active.
        checkSlides(3, 1),
    ]
);

registerWebsitePreviewTour("snippet_carousel_autoplay", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({id: "s_carousel", name: "Carousel", groupName: "Intro"}),
    ...clickOnSnippet(".carousel .carousel-item.active"),
    {
        content: "Decrease the interval between slides",
        trigger: "div[data-label='Speed'] input",
        run: 'edit 3',
    },
    {
        content: "Enable the autoplay option",
        trigger: "div[data-label='Autoplay'] input",
        run: 'click',
    },
    ...clickOnSave(),
    {
        content: "Check if the first slide is active and wait for 3s",
        trigger: `${carouselInnerSelector} > div.active:nth-child(1)`,
        run: () => new Promise(resolve => setTimeout(resolve, 3000)),
    },
    {
        content: "Check if the second slide is active",
        trigger: `${carouselInnerSelector} > div.active:nth-child(2)`,
    },
]);

registerWebsitePreviewTour(
    "snippet_carousel_linkable_slides",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_carousel", name: "Carousel", groupName: "Intro" }),
        ...clickOnSnippet(".carousel .carousel-item.active"),
        {
            content: "Make the Slide linkable",
            trigger: "div[data-action-id='setSlideLink'] input",
            run: "click",
        },
        {
            content: "Enter the URL to be linked with slide",
            trigger: "div[data-attribute-action='href'] input[title='Your URL']",
            run: "edit /contactus",
        },
        {
            content: "Select the URL from autocomplete dropdown",
            trigger:
                "ul.ui-autocomplete li div:contains('/contactus-thank-you (Thanks (Contact us))')",
            run: "click",
        },
        {
            content: "Enable opening the link in a new tab",
            trigger: "div[data-label='Open in New Tab'] div[data-attribute-action='target'] input",
            run: "click",
        },
        {
            content: "Open the color picker",
            trigger: "div[data-label='Hover Effect'] .o_we_color_preview",
            run: "click",
        },
        {
            content: "Switch to the Custom tab in the color picker",
            trigger: `.o_popover .o_font_color_selector .btn-tab:contains("Custom")`,
            run: "click",
        },
        {
            content: "Pick hover background color",
            trigger: ".o_popover .o_color_picker_inputs .o_hex_div input",
            run: `edit ${ANCHOR_HOVER_BG_COLOR}`,
        },
        ...clickOnSave(),
        {
            content: "Check that the anchor tag is added to the carousel item",
            trigger:
                ":iframe .carousel-item div.slide-link-wrapper a.slide-link[href='/contactus-thank-you'][target='_blank']",
        },
        {
            content: "Check that the hover effect is applied",
            trigger: `:iframe .carousel-item div.slide-link-wrapper a.slide-link.slide-link-hover[style='--slide-hover-bg-color: ${ANCHOR_HOVER_BG_COLOR};']`,
        },
        {
            content: "Click the button behind the slide anchor",
            trigger: `:iframe .carousel-item a:contains("Contact Us")`,
            run: function () {
                const rect = this.anchor.getBoundingClientRect();

                const x = rect.left + rect.width / 2;
                const y = rect.top + rect.height / 2;

                const clickEvent = new MouseEvent("click", {
                    bubbles: true,
                    cancelable: true,
                    clientX: x,
                    clientY: y,
                    view: window,
                });

                const iframeContent = this.anchor.ownerDocument;
                const targetEl = iframeContent.querySelector(".slide-link");
                // Trigger anchor's handler to forward click to the
                // button behind it.
                targetEl.dispatchEvent(clickEvent);
            },
        },
        {
            content: "Verify that the click navigated to the Contact Us page.",
            trigger: ":iframe [data-view-xmlid='website.contactus']",
        },
    ]
);
