import {
    changeOptionInPopover,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';
import { goToCart } from '@website_sale/js/tours/tour_utils';

const productsSnippet = {
    name: "Products Carousel",
    id: "s_dynamic_snippet_products_carousal",
    groupName: "eCommerce",
};

const productsGridSnippet = {
    name: "Products Grid",
    id: "s_dynamic_snippet_products_grid",
    groupName: "eCommerce",
};

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

registerWebsitePreviewTour("website_sale.snippet_products_grid", { edition: true }, () => [
    ...insertSnippet(productsGridSnippet),
    {
        content: "Verify that the products grid snippet is present",
        trigger:
            ":iframe .s_dynamic_snippet_products_grid[data-grid-columns='3'][data-mobile-columns='2']",
    },
    {
        content: "Verify that the products grid layout is rendered",
        trigger: ":iframe .s_dynamic_snippet_products_grid .s_dynamic_snippet_grid_container",
    },
    {
        content: "Verify that the carousel layout is not rendered",
        trigger: ":iframe .s_dynamic_snippet_products_grid:not(:has(.carousel))",
    },
    ...clickOnSnippet(productsGridSnippet),
    {
        content: "Verify desktop grid columns option is available",
        trigger: "#o_wsale_grid_columns",
    },
    {
        content: "Verify mobile grid columns option is available",
        trigger: "#o_wsale_mobile_columns",
    },
    ...clickOnSave(),
]);

registerWebsitePreviewTour(
    'website_sale.products_snippet_recently_viewed',
    {
        edition: true,
    },
    () => [
        ...insertSnippet(productsSnippet),
        ...clickOnSnippet(productsSnippet),
        ...changeOptionInPopover(productsSnippet.name, "Filter", "Recently Viewed"),
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
