import {
    changeOptionInPopover,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';
import { goToCart } from '@website_sale/js/tours/tour_utils';

const productsSnippet = {id: "s_dynamic_snippet_products", name: "Products", groupName: "Catalog"};

registerWebsitePreviewTour('website_sale.snippet_products', {
    url: '/',
    edition: true,
},
() => {
    return [
        ...insertSnippet(productsSnippet),
        ...clickOnSnippet(productsSnippet),
        ...clickOnSave(),
        {
            trigger: ":iframe .s_dynamic_snippet_products .o_carousel_product_card .js_add_cart:not(:visible)",
            run: 'click',
        },
        goToCart({ backend: true, expectUnloadPage: false }),
    ]
});

registerWebsitePreviewTour('website_sale.products_snippet_recently_viewed', {
    url: '/',
    edition: true,
},
() => [
    ...insertSnippet(productsSnippet),
    ...clickOnSnippet(productsSnippet),
    ...changeOptionInPopover("Products", "Filter", "Recently Viewed"),
    ...clickOnSave(),
    {
        content: 'make delete icon appear',
        trigger: ':iframe .s_dynamic_snippet_products .o_carousel_product_card',
        run({ queryFirst }) {
            queryFirst(
                `:iframe .o_carousel_product_card[aria-label="Storage Box"] .js_remove`,
            ).style.display = "block";
        }
    },
    {
        trigger: ':iframe .s_dynamic_snippet_products .o_carousel_product_card .js_remove',
        run: 'click',
    },
]);
