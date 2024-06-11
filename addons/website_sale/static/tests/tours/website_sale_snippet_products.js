/** @odoo-module */

import wTourUtils from '@website/js/tours/tour_utils';
import wSaleTourUtils from '@website_sale/js/tours/tour_utils';

const optionBlock = 'dynamic_snippet_products';
const productsSnippet = {id: 's_dynamic_snippet_products', name: 'Products'};
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
        wTourUtils.changeOption(optionBlock, 'we-select[data-name="template_opt"] we-toggler', 'template'),
        wTourUtils.changeOption(optionBlock, `we-button[data-select-data-attribute="website_sale.${templateKey}"]`),
        {
            content: 'Check the template is applied',
            trigger: `iframe .s_dynamic_snippet_products.${templateClass} .carousel`,
            run: () => null, // It's a check
        },
    ];
}

wTourUtils.registerWebsitePreviewTour('website_sale.snippet_products', {
    test: true,
    url: '/',
    edition: true,
},
() => {
    let templatesSteps = [];
    for (const templateKey of templates) {
        templatesSteps = templatesSteps.concat(changeTemplate(templateKey));
    }
    return [
        wTourUtils.dragNDrop(productsSnippet),
        wTourUtils.clickOnSnippet(productsSnippet),
        ...templatesSteps,
        ...changeTemplate('dynamic_filter_template_product_product_add_to_cart'),
        ...wTourUtils.clickOnSave(),
        {
            trigger: "iframe .s_dynamic_snippet_products .o_carousel_product_card_body .js_add_cart",
            run: 'click',
        },
        wSaleTourUtils.goToCart({backend: true}),
    ]
});

wTourUtils.registerWebsitePreviewTour('website_sale.products_snippet_recently_viewed', {
    test: true,
    url: '/',
    edition: true,
},
() => [
    wTourUtils.dragNDrop(productsSnippet),
    wTourUtils.clickOnSnippet(productsSnippet),
    ...changeTemplate('dynamic_filter_template_product_product_add_to_cart'),
    wTourUtils.changeOption(optionBlock, 'we-select[data-name="filter_opt"] we-toggler', 'filter'),
    wTourUtils.changeOption(optionBlock, 'we-select[data-name="filter_opt"] we-button:contains("Recently Viewed")', 'filter'),
    ...wTourUtils.clickOnSave(),
    {
        content: 'make delete icon appear',
        trigger: 'iframe .s_dynamic_snippet_products .o_carousel_product_card',
        run: function () {
            const $iframe = $('.o_iframe').contents();
            const $productCard = $iframe.find('.o_carousel_product_card:has(a img[alt="Storage Box"])');
            console.log($productCard);
            $productCard.find('.js_remove').attr('style', 'display: block;');
        }
    },
    {
        trigger: 'iframe .s_dynamic_snippet_products .o_carousel_product_card .js_remove',
        run: 'click',
    },
]);
