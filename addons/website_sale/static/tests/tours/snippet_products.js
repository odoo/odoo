import {
    changeOptionInPopover,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';
import { goToCart } from '@website_sale/js/tours/tour_utils';

const productsSnippet = { id: "s_dynamic_snippet_products", name: "Products", groupName: "Catalog" };

registerWebsitePreviewTour(
    'website_sale.snippet_products',
    {
        edition: true,
    },
    () => {
        return [
            ...insertSnippet(productsSnippet),
            {
                content:
                    "Verify that the `o_dynamic_snippet_carousel` class is present, as it renders two elements when the title is left & the content width is not max.",
                trigger: ":iframe .o_dynamic_snippet_carousel",
            },
            ...clickOnSnippet(productsSnippet),
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
