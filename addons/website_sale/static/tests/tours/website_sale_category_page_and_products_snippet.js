/** @odoo-modules */

import { clickOnSave, registerWebsitePreviewTour } from '@website/js/tours/tour_utils';
import { registry } from "@web/core/registry";

const PRODUCT_CATEGORY_ID = 2;

registerWebsitePreviewTour('category_page_and_products_snippet_edition', {
    url: `/shop/category/${PRODUCT_CATEGORY_ID}`,
    edition: true,
}, () => [
    {
        trigger: ".o_website_preview.editor_enable.editor_has_snippets",
    },
    {
        content: "Drag and drop the Products snippet group inside the category area.",
        trigger: '#oe_snippets .oe_snippet[name="Products"] .oe_snippet_thumbnail:not(.o_we_ongoing_insertion)',
        run: "drag_and_drop :iframe #category_header",
    },
    {
        content: "Click on the s_dynamic_snippet_products snippet.",
        trigger: ':iframe .o_snippet_preview_wrap[data-snippet-id="s_dynamic_snippet_products"]',
        run: "click",
    },

    {
        content: "Click on the product snippet to show its options",
        trigger: ':iframe #category_header .s_dynamic_snippet_products',
        run: "click",
    },
    {
        content: "Open category option dropdown",
        trigger: 'we-select[data-attribute-name="productCategoryId"] we-toggler',
        run: "click",
    },
    {
        content: "Choose the option to use the current page's category",
        trigger: 'we-button[data-select-data-attribute="current"]',
        run: "click",
    },
    ...clickOnSave(),
]);

registry.category("web_tour.tours").add('category_page_and_products_snippet_use', {
    url: `/shop/category/${PRODUCT_CATEGORY_ID}`,
    steps: () => [
    {
        content: "Check that the snippet displays the right products",
        // Wait for at least one shown product
        trigger: '#category_header .s_dynamic_snippet_products:has(.o_carousel_product_img_link)',
        run() {
            // Note: this could be more robust to not rely on demo data and
            // make sure that the newest products are not by chance all of
            // the second category (used for the test) and ... but should be ok.
            const productGridEl = this.anchor.closest("#products_grid");
            const regex = new RegExp(`^/shop/[\\w-/]+-(\\d+)\\?category=${PRODUCT_CATEGORY_ID}$`);
            const allPageProductIDs = [...productGridEl.querySelectorAll('.oe_product_image_link')]
                .map(el => el.getAttribute('href').match(regex)[1]);

            const $shownProductLinks = this.anchor.querySelectorAll(".o_carousel_product_img_link");
            const regex2 = new RegExp(`^/shop/[\\w-/]+-(\\d+)(?:#attribute_values=\\d*)?$`);
            for (const shownProductLinkEl of $shownProductLinks) {
                const productID = shownProductLinkEl.getAttribute('href').match(regex2)[1];
                if (!allPageProductIDs.includes(productID)) {
                    console.error(`The snippet displays a product (${productID}) which does not belong to the current category (${allPageProductIDs})`);
                }
            }
        },
    },
]});
