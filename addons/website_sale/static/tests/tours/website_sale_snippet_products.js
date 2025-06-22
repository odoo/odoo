import { queryFirst } from '@odoo/hoot-dom';
import {
    changeOptionInPopover,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';
import { goToCart } from '@website_sale/js/tours/tour_utils';

const productsSnippet = {id: "s_dynamic_snippet_products", name: "Products", groupName: "Catalog"};
const templates = [
    "dynamic_filter_template_product_product_add_to_cart",
    "dynamic_filter_template_product_product_view_detail",
    "dynamic_filter_template_product_product_mini_image",
    "dynamic_filter_template_product_product_mini_price",
    "dynamic_filter_template_product_product_mini_name",
    "dynamic_filter_template_product_product_centered",
    "dynamic_filter_template_product_product_borderless_1",
    "dynamic_filter_template_product_product_borderless_2",
    "dynamic_filter_template_product_product_banner",
    "dynamic_filter_template_product_product_horizontal_card",
    "dynamic_filter_template_product_product_horizontal_card_2",
    "dynamic_filter_template_product_product_card_group",
];

function changeTemplate(templateKey) {
    const templateClass = templateKey.replace(/dynamic_filter_template_/, "s_");
    return [
        ...changeOptionInPopover("Products", "Template", `div[data-action-param*="${templateKey}"]`),
        {
            content: 'Check the template is applied',
            trigger: `:iframe .s_dynamic_snippet_products.${templateClass} .carousel`,
        },
    ];
}

registerWebsitePreviewTour('website_sale.snippet_products', {
    url: '/',
    edition: true,
},
() => {
    let templatesSteps = [];
    for (const templateKey of templates) {
        templatesSteps = templatesSteps.concat(changeTemplate(templateKey));
    }
    return [
        ...insertSnippet(productsSnippet),
        ...clickOnSnippet(productsSnippet),
        ...templatesSteps,
        ...changeTemplate('dynamic_filter_template_product_product_add_to_cart'),
        ...clickOnSave(),
        {
            trigger: ":iframe .s_dynamic_snippet_products .o_carousel_product_card_body .js_add_cart",
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
    ...changeTemplate('dynamic_filter_template_product_product_add_to_cart'),
    ...changeOptionInPopover("Products", "Filter", "Recently Viewed"),
    ...clickOnSave(),
    {
        content: 'make delete icon appear',
        trigger: ':iframe .s_dynamic_snippet_products .o_carousel_product_card',
        run() {
            queryFirst(
                `:iframe .o_carousel_product_card:has(a img[alt="Storage Box"]) .js_remove`,
            ).style.display = "block";
        }
    },
    {
        trigger: ':iframe .s_dynamic_snippet_products .o_carousel_product_card .js_remove',
        run: 'click',
    },
]);
