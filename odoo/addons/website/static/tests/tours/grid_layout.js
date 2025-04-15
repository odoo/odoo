/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

const snippet = {
    id: 's_text_image',
    name: 'Text - Image',
};

wTourUtils.registerWebsitePreviewTour('website_replace_grid_image', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    wTourUtils.dragNDrop(snippet),
    wTourUtils.clickOnSnippet(snippet),
    {
        content: "Toggle to grid mode",
        trigger: '.o_we_user_value_widget[data-name="grid_mode"]',
    },
    {
        content: "Replace image",
        trigger: 'iframe .s_text_image img',
        run: 'dblclick',
    },
    {
        content: "Pick new image",
        trigger: '.o_select_media_dialog img[title="s_banner_default_image.jpg"]',
    },
    {
        content: "Add new image column",
        trigger: '.o_we_user_value_widget[data-add-element="image"]',
    },
    {
        content: "Replace new image",
        trigger: 'iframe .s_text_image img[src="/web/image/website.s_text_image_default_image"]',
        run: 'dblclick',
    },
    {
        content: "Pick new image",
        trigger: '.o_select_media_dialog img[title="s_banner_default_image.jpg"]',
    },
    ...wTourUtils.clickOnSave()
]);

wTourUtils.registerWebsitePreviewTour("scroll_to_new_grid_item", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    // Drop enough snippets to scroll.
    wTourUtils.dragNDrop({id: "s_text_image", name: "Text - Image"}),
    wTourUtils.dragNDrop({id: "s_image_text", name: "Image - Text"}),
    wTourUtils.dragNDrop({id: "s_image_text", name: "Image - Text"}),
    // Toggle the first snippet to grid mode.
    wTourUtils.clickOnSnippet({id: "s_text_image", name: "Text - Image"}),
    wTourUtils.changeOption("layout_column", 'we-button[data-name="grid_mode"]'),
    // Add a new grid item.
    wTourUtils.changeOption("layout_column", 'we-button[data-add-element="image"]'),
    {
        content: "Check that the page scrolled to the new grid item",
        trigger: "iframe .s_text_image .o_grid_item:nth-child(3)",
        run: function () {
            // Leave some time to the page to scroll.
            setTimeout(() => {
                const newItemPosition = this.$anchor[0].getBoundingClientRect();
                if (newItemPosition.top < 0) {
                    console.error("The page did not scroll to the new grid item.");
                }
                document.body.classList.add("o_scrolled_to_grid_item");
            }, 500);
        },
    }, {
        content: "Make sure the scroll check is done",
        trigger: ".o_scrolled_to_grid_item",
        isCheck: true,
    },
]);
