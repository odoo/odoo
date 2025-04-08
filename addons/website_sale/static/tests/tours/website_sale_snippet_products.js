import { queryFirst } from "@odoo/hoot-dom";
import {
    changeOption,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";
import { goToCart } from "@website_sale/js/tours/tour_utils";

const optionBlock = "dynamic_snippet_products";
const productsSnippet = (layout) => ({
    id: `s_dynamic_snippet_products_${layout || "add_to_cart"}`,
    name: "Products",
    groupName: "Products",
});
const snippetLayouts = [
    "view_detail",
    "mini_image",
    "mini_price",
    "mini_name",
    "centered",
    "borderless_1",
    "borderless_2",
    "banner",
    "horizontal_card",
    "horizontal_card_2",
    "card_group",
];

function changeSnippetLayout(layout) {
    return [
        {
            content: "Replace the current snippet.",
            trigger: ":iframe .oe_overlay.oe_active .o_snippet_replace",
            run: "click",
        },
        {
            content: "Select the new snippet",
            trigger: `:iframe .o_snippet_preview_wrap[data-snippet-id="s_dynamic_snippet_products_${layout}"]:not(.d-none)`,
            run: "click",
        },
        ...clickOnSnippet(productsSnippet(layout)),
    ];
}

registerWebsitePreviewTour("website_sale.snippet_products", {
    url: "/",
    edition: true,
},
() => {
    let snippetLayoutSteps = [];
    const continueSelector = `button[name="website_sale_product_configurator_continue_button"]`;
    const goToCartStep = goToCart({ backend: true });
    for (const layout of snippetLayouts) {
        snippetLayoutSteps = snippetLayoutSteps.concat(changeSnippetLayout(layout));
    }
    return [
        ...insertSnippet(productsSnippet()),
        ...clickOnSnippet(productsSnippet()),
        ...snippetLayoutSteps,
        ...changeSnippetLayout("add_to_cart"),
        ...clickOnSave(),
        {
            trigger: ":iframe .s_dynamic_snippet_products_add_to_cart .o_carousel_product_card_body .js_add_cart",
            run: "click",
        },
        {
            ...goToCartStep,
            trigger: `${goToCartStep.trigger}, :iframe ${continueSelector}`,
            run: (helpers) => {
                document.querySelector(continueSelector)?.click();
                helpers.click();
            }
        },
    ]
});

registerWebsitePreviewTour("website_sale.products_snippet_recently_viewed", {
    url: "/",
    edition: true,
},
() => [
    ...insertSnippet(productsSnippet()),
    ...clickOnSnippet(productsSnippet()),
    changeOption(optionBlock, `we-select[data-name="filter_opt"] we-toggler`, "filter"),
    changeOption(optionBlock, `we-select[data-name="filter_opt"] we-button:contains("Recently Viewed")`, "filter"),
    ...clickOnSave(),
    {
        content: "make delete icon appear",
        trigger: ":iframe .s_dynamic_snippet_products_add_to_cart .o_carousel_product_card",
        run() {
            queryFirst(
                `:iframe .o_carousel_product_card:has(a img[alt="Storage Box"]) .js_remove`,
            ).style.display = "block";
        }
    },
    {
        trigger: ":iframe .s_dynamic_snippet_products_add_to_cart .o_carousel_product_card .js_remove",
        run: "click",
    },
]);
