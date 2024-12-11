/** @odoo-modules */

import wTourUtils from '@website/js/tours/tour_utils';
import { registry } from "@web/core/registry";


wTourUtils.registerWebsitePreviewTour('category_page_and_products_snippet_edition', {
    test: true,
    url: '/shop',
}, () => [
    {
        content: "Navigate to category",
        trigger: 'iframe .o_wsale_filmstip > li:contains("Test Category")',
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    Object.assign(wTourUtils.dragNDrop({id: 's_dynamic_snippet_products', name: 'Products'}), {
        content: "Drag and drop the product snippet inside the category area",
        run: 'drag_and_drop_native iframe #category_header',
    }),
    {
        content: "Click on the product snippet to show its options",
        trigger: 'iframe #category_header .s_dynamic_snippet_products',
    },
    {
        content: "Open category option dropdown",
        trigger: 'we-select[data-attribute-name="productCategoryId"] we-toggler',
    },
    {
        content: "Choose the option to use the current page's category",
        trigger: 'we-button[data-select-data-attribute="current"]',
    },
    ...wTourUtils.clickOnSave(),
]);

registry.category("web_tour.tours").add('category_page_and_products_snippet_use', {
    test: true,
    url: '/shop',
    steps: () => [
    {
        content: "Navigate to category",
        trigger: '.o_wsale_filmstip > li:contains("Test Category")',
    },
    {
        content: "Check that the snippet displays the right products",
        // Wait for at least one shown product
        trigger: '#category_header .s_dynamic_snippet_products:has(.o_carousel_product_img_link)',
        run: function () {
            // Fetch the category's id from the url.
            const productCategoryId = window.location.href.match('/shop/category/test-category-(\\d+)')[1]
            const productGridEl = this.$anchor[0].closest('#products_grid');
            const regex = new RegExp(`^/shop/[\\w-/]+-(\\d+)\\?category=${productCategoryId}$`);
            const allPageProductIDs = [...productGridEl.querySelectorAll('.oe_product_image_link')]
                .map(el => el.getAttribute('href').match(regex)[1]);

            const $shownProductLinks = this.$anchor.find('.o_carousel_product_img_link');
            const regex2 = new RegExp(`^/shop/[\\w-/]+-(\\d+)(?:#attr=\\d*)?$`);
            for (const shownProductLinkEl of $shownProductLinks) {
                const productID = shownProductLinkEl.getAttribute('href').match(regex2)[1];
                if (!allPageProductIDs.includes(productID)) {
                    console.error(`The snippet displays a product (${productID}) which does not belong to the current category (${allPageProductIDs})`);
                }
            }
        },
    },
]});
