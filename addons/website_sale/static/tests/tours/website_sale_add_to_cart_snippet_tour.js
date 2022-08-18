/** @odoo-module **/

import wsTourUtils from 'website_sale.tour_utils';
import wTourUtils from 'website.tour_utils';

function editAddToCartSnippet() {
    return [
        wTourUtils.clickOnEdit(),
        wTourUtils.clickOnSnippet({id: 's_add_to_cart'})
    ]
}

wTourUtils.registerEditionTour('add_to_cart_snippet_tour', {
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

        // Product with 2 variants with visitor choice (will open modal)
        ...editAddToCartSnippet(),
        ...wTourUtils.selectElementInWeSelectWidget('product_template_picker_opt', 'Conference Chair', true),
        ...wTourUtils.clickOnSave(),
        wTourUtils.clickOnElement('add to cart button', 'iframe .s_add_to_cart_btn'),
        wTourUtils.clickOnElement('continue shopping', 'iframe span:contains(Continue Shopping)'),

        // Product with 2 variants with a variant selected
        ...editAddToCartSnippet(),
        ...wTourUtils.selectElementInWeSelectWidget('product_template_picker_opt', 'Conference Chair', true),
        ...wTourUtils.selectElementInWeSelectWidget('product_variant_picker_opt', 'Conference Chair (Aluminium)'),
        ...wTourUtils.clickOnSave(),
        wTourUtils.clickOnElement('add to cart button', 'iframe .s_add_to_cart_btn'),

        // Basic product with no variants and action=buy now
        ...editAddToCartSnippet(),
        ...wTourUtils.selectElementInWeSelectWidget('product_template_picker_opt', 'Acoustic Bloc Screens', true),
        ...wTourUtils.selectElementInWeSelectWidget('action_picker_opt', 'Buy Now'),
        ...wTourUtils.clickOnSave(),
        wTourUtils.clickOnElement('add to cart button', 'iframe .s_add_to_cart_btn'),
        wTourUtils.assertPathName('/shop/payment', 'button[name=o_payment_submit_button]'),

        wsTourUtils.goToCart({quantity: 4, backend: false}),
        wsTourUtils.assertCartContains({productName: 'Acoustic Bloc Screens'}),
        wsTourUtils.assertCartContains({productName: 'Conference Chair (Steel)'}),
        wsTourUtils.assertCartContains({productName: 'Conference Chair (Aluminium)'}),
    ],
);
