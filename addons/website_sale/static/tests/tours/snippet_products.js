import {
    changeOptionInPopover,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';
import { goToCart } from '@website_sale/js/tours/tour_utils';

const productsSnippet = { id: "s_dynamic_snippet_products", name: "Products", groupName: "eCommerce" };

registerWebsitePreviewTour(
    'website_sale.snippet_products',
    {
        edition: true,
    },
    () => {
        return [
            ...insertSnippet(productsSnippet),
            {
                content: "Verify that the `o_dynamic_carousel_snippet` class is present",
                trigger: ":iframe .o_dynamic_carousel_snippet",
            },
            ...clickOnSnippet(productsSnippet),
            {
                content: "Verify section title top is selected by default",
                trigger: "button[data-action-param='d-flex justify-content-between'].active",
            },
            ...clickOnSave(),
            {
                trigger: ":iframe .s_dynamic_snippet_products .o_carousel_product_card button[name='add_to_cart']:not(:visible)",
                run: 'click',
            },
            goToCart({ backend: true, expectUnloadPage: false }),
        ]
    }
);

registerWebsitePreviewTour(
    'website_sale.products_snippet_recently_viewed',
    {
        edition: true,
    },
    () => [
        ...insertSnippet(productsSnippet),
        ...clickOnSnippet(productsSnippet),
        ...changeOptionInPopover("Products", "Filter", "Recently Viewed"),
        {
            content: 'check product are shown in edit',
            trigger:
                ':iframe .s_dynamic_snippet_products .s_dynamic_snippet_content .o_carousel_product_card[aria-label="Storage Box"]',
        },
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
    ]
);
