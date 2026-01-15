import { registry } from "@web/core/registry";
import { clickOnSave, clickOnEditAndWaitEditMode, registerWebsitePreviewTour } from '@website/js/tours/tour_utils';


registerWebsitePreviewTour('category_page_and_products_snippet_edition', {
    url: '/shop',
}, () => [
    {
        content: "Navigate to category",
        trigger: ':iframe .o_wsale_filmstrip > li:contains("Test Category") > a',
        run: "click",
    },
    {
        content: "Wait for page to load",
        trigger: ":iframe h1:contains('Test Category'):not(:visible)",
    },
    ...clickOnEditAndWaitEditMode(),
    {
        trigger: ".o-website-builder_sidebar .o_snippets_container .o_snippet",
    },
    {
        content: "Drag and drop the Products snippet group inside the category area.",
        trigger: ".o_block_tab:not(.o_we_ongoing_insertion) .o_snippet[name='Catalog'] .o_snippet_thumbnail",
        run: "drag_and_drop :iframe #category_header",
    },
    {
        content: "Click on the s_dynamic_snippet_products snippet.",
        trigger: ':iframe .o_snippet_preview_wrap[data-snippet-id="s_dynamic_snippet_products"]',
        run: "click",
    },
    {
        trigger: ":iframe:not(:has(.o_loading_screen))",
    },
    {
        content: "Click on the product snippet to show its options",
        trigger: ':iframe #category_header .s_dynamic_snippet_products',
        run: "click",
    },
    {
        content: "Open category option dropdown",
        trigger: "button[id='product_category_opt']",
        run: "click",
    },
    {
        content: "Choose the option to use the current page's category",
        trigger: "div.o-dropdown-item:contains('Current Category or All')",
        run: "click",
    },
    ...clickOnSave(),
]);

registry.category("web_tour.tours").add('category_page_and_products_snippet_use', {
    url: '/shop',
    steps: () => [
    {
        content: "Navigate to category",
        trigger: '.o_wsale_filmstrip > li:contains("Test Category") > a',
        run: "click",
        expectUnloadPage: true,
    },
    {
        content: "Check that the snippet displays the right products",
        // Wait for at least one shown product
        trigger: '#category_header .s_dynamic_snippet_products:has(.oe_product_image_link)',
        run() {
            // Fetch the category's id from the url.
            const productCategoryId = window.location.href.match('/shop/category/test-category-(\\d+)')[1];
            const productGridEl = document.getElementById('o_wsale_products_grid');
            const regex = new RegExp(`^/shop/test-category-${productCategoryId}/[\\w-/]+-(\\d+)$`);
            const allPageProductIDs = [...productGridEl.querySelectorAll('.oe_product_image_link')]
                .map(el => el.getAttribute('href').match(regex)[1]);

            const $shownProductLinks = this.anchor.querySelectorAll(".s_dynamic_snippet_products .oe_product_image_link");
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
