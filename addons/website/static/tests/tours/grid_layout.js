import {
    changeOption,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

const snippet = {
    id: 's_text_image',
    name: 'Text - Image',
    groupName: "Content",
};

registerWebsitePreviewTour('website_replace_grid_image', {
    url: '/',
    edition: true,
}, () => [
    ...insertSnippet(snippet),
    {
        // TODO: should check if o_loading_screen is not present (TO check with PIPU)
        // Await step in the history
        trigger: `:iframe:has(#wrap[contenteditable='true'])`,
    },
    ...clickOnSnippet(snippet),
    {
        content: "Toggle to grid mode",
        trigger: "[data-action-id='setGridLayout']",
        run: "click",
    },
    {
        content: "Replace image",
        trigger: ':iframe .s_text_image img',
        run: 'dblclick',
    },
    {
        content: "Pick new image",
        trigger: '.o_select_media_dialog .o_button_area[aria-label="s_banner_default_image.jpg"]',
        run: "click",
    },
    {
        content: "Add new image column",
        trigger: "[data-action-id='addGridElement'][data-action-param='image']",
        run: "click",
    },
    {
        content: "Pick new image",
        trigger: '.o_select_media_dialog .o_button_area[aria-label="s_banner_default_image2.webp"]',
        run: "click",
    },
    {
        content: "Replace new image",
        trigger: ':iframe .s_text_image img[src*="s_banner_default_image2.webp"]',
        run: 'dblclick',
    },
    {
        content: "Pick new image",
        trigger: '.o_select_media_dialog .o_button_area[aria-label="s_banner_default_image.jpg"]',
        run: "click",
    },
    ...clickOnSave()
]);

registerWebsitePreviewTour("scroll_to_new_grid_item", {
    url: "/",
    edition: true,
}, () => [
    // Drop enough snippets to scroll.
    ...insertSnippet({id: "s_text_image", name: "Text - Image", groupName: "Content"}),
    ...insertSnippet({id: "s_image_text", name: "Image - Text", groupName: "Content"}),
    ...insertSnippet({id: "s_image_text", name: "Image - Text", groupName: "Content"}),
    // Toggle the first snippet to grid mode.
    ...clickOnSnippet({id: "s_text_image", name: "Text - Image"}),
    changeOption("Text - Image", "setGridLayout"),
    // Add a new grid item.
    changeOption("Text - Image", "[data-action-id='addGridElement'][data-action-param='image']"),
    {
        content: "Select the new image in the media dialog",
        trigger: '.o_select_media_dialog .o_button_area[aria-label="s_banner_default_image.jpg"]',
        run: "click",
    }, {
        content: "Check that the page scrolled to the new grid item",
        trigger: ":iframe .s_text_image .o_grid_item:nth-child(3)",
        async run() {
            // Leave some time to the page to scroll.
            await new Promise((r) => setTimeout(r, 500));
            const newItemPosition = this.anchor.getBoundingClientRect();
            if (newItemPosition.top < 0) {
                throw new Error("The page did not scroll to the new grid item.");
            }
            document.body.classList.add("o_scrolled_to_grid_item");
        },
    }, {
        content: "Make sure the scroll check is done",
        trigger: ".o_scrolled_to_grid_item",
    },
    ...clickOnSave(),
]);
