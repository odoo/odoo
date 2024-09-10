/** @odoo-module **/

import wsTourUtils from 'website_sale.tour_utils';
import wTourUtils from 'website.tour_utils';

function editAddToCartSnippet() {
    return [
        ...wTourUtils.clickOnEditAndWaitEditMode(),
        wTourUtils.clickOnSnippet({id: 's_add_to_cart'})
    ]
}

wTourUtils.registerWebsitePreviewTour('add_to_cart_snippet_tour', {
        url: '/',
        edition: true,
        test: true,
    },
    [
        wTourUtils.dragNDrop({name: 'Add to Cart Button'}),

        // Basic product with no variants
        wTourUtils.clickOnSnippet({id: 's_add_to_cart'}),
        ...wTourUtils.selectElementInWeSelectWidget('product_template_picker_opt', 'Acoustic Bloc Screens', true),
        ...wTourUtils.clickOnSave(),
        wTourUtils.clickOnElement('add to cart button', 'iframe .s_add_to_cart_btn'),
        {
            trigger: "iframe nav li.o_wsale_my_cart sup:contains(1)",
            run: () => null,
        },
        // Product with 2 variants with visitor choice (will open modal)
        ...editAddToCartSnippet(),
        ...wTourUtils.selectElementInWeSelectWidget('product_template_picker_opt', 'Conference Chair', true),
        ...wTourUtils.clickOnSave(),
        wTourUtils.clickOnElement('add to cart button', 'iframe .s_add_to_cart_btn'),
        wTourUtils.clickOnElement('continue shopping', 'iframe span:contains(Continue Shopping)'),
        {
            trigger: "body:not(:has(.modal))",
            run: () => null,
        },
        {
            trigger: "iframe nav li.o_wsale_my_cart sup:contains(2)",
            run: () => null,
        },

        // Product with 2 variants with a variant selected
        ...editAddToCartSnippet(),
        ...wTourUtils.selectElementInWeSelectWidget('product_template_picker_opt', 'Conference Chair', true),
        {
            run: () => null,
            trigger:
                `we-select[data-name=product_variant_picker_opt] we-toggler:contains("Visitor's Choice")`,
        },
        ...wTourUtils.selectElementInWeSelectWidget('product_variant_picker_opt', 'Conference Chair (Aluminium)'),
        ...wTourUtils.clickOnSave(),
        wTourUtils.clickOnElement('add to cart button', 'iframe .s_add_to_cart_btn'),
        {
            trigger: "iframe nav li.o_wsale_my_cart sup:contains(3)",
            run: () => null,
        },

        // Basic product with no variants and action=buy now
        ...editAddToCartSnippet(),
        ...wTourUtils.selectElementInWeSelectWidget('product_template_picker_opt', 'Acoustic Bloc Screens', true),
        {
            run: () => null,
            trigger:
                `we-select[data-name=action_picker_opt] we-toggler:contains("Add to Cart")`,
        },
        ...wTourUtils.selectElementInWeSelectWidget('action_picker_opt', 'Buy Now'),
        ...wTourUtils.clickOnSave(),
        wTourUtils.clickOnElement('add to cart button', 'iframe .s_add_to_cart_btn'),
        {
            // wait for the page to load, as the next check was sometimes too fast
            content: "Wait for the redirection to the payment page",
            trigger: "div:contains(Choose a delivery method)",
            run: () => null,
        },
        wTourUtils.assertPathName('/shop/payment', 'button[name=o_payment_submit_button]'),

        wsTourUtils.goToCart({quantity: 4, backend: false}),
        wsTourUtils.assertCartContains({productName: 'Acoustic Bloc Screens'}),
        wsTourUtils.assertCartContains({productName: 'Conference Chair (Steel)'}),
        wsTourUtils.assertCartContains({productName: 'Conference Chair (Aluminium)'}),
    ],
);
