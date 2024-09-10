/** @odoo-module **/

import wsTourUtils from '@website_sale/js/tours/tour_utils';
import wTourUtils from '@website/js/tours/tour_utils';

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
    () => [
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
        // ...editAddToCartSnippet(),
        // ...wTourUtils.selectElementInWeSelectWidget('product_template_picker_opt', 'Conference Chair', true),
        // ...wTourUtils.selectElementInWeSelectWidget('product_variant_picker_opt', 'Conference Chair (Aluminium)'),
        // ...wTourUtils.clickOnSave(),
        // wTourUtils.clickOnElement('add to cart button', 'iframe .s_add_to_cart_btn'),
        // TODO edm: re-enable this part when this isn't an indeterminist error anymore

        // Basic product with no variants and action=buy now
        ...editAddToCartSnippet(),
        ...wTourUtils.selectElementInWeSelectWidget('product_template_picker_opt', 'Acoustic Bloc Screens', true),
        ...wTourUtils.selectElementInWeSelectWidget('action_picker_opt', 'Buy Now'),
        ...wTourUtils.clickOnSave(),
        wTourUtils.clickOnElement('add to cart button', 'iframe .s_add_to_cart_btn'),
        {
            content: "Wait for the redirection to the payment page",
            trigger: 'body',
            isCheck: true,  // wait for the page to load, as the next check was sometimes too fast
        },
<<<<<<< 17.0
        wTourUtils.assertPathName('/shop/payment', 'iframe a[href="/shop/cart"]'),

        wsTourUtils.goToCart({quantity: 3, backend: true}),
        wsTourUtils.assertCartContains({productName: 'Acoustic Bloc Screens', backend: true}),
        wsTourUtils.assertCartContains({productName: 'Conference Chair (Steel)', backend: true}),
        // wsTourUtils.assertCartContains({productName: 'Conference Chair (Aluminium)', backend: true}),
||||||| c226098a20e9d70090bc9ae6b4c2b82483ae0f4b
        {
            content: `Check if we have been redirected to /shop/payment`,
            trigger: `button[name=o_payment_submit_button]`,
            run: () => {
                if (!window.location.pathname.startsWith("/shop/payment")) {
                    console.error(`We should be on /shop/payment.`);
                }
            },
        },
        wsTourUtils.goToCart({quantity: 4, backend: false}),
        wsTourUtils.assertCartContains({productName: 'Acoustic Bloc Screens'}),
        wsTourUtils.assertCartContains({productName: 'Conference Chair (Steel)'}),
        wsTourUtils.assertCartContains({productName: 'Conference Chair (Aluminium)'}),
=======
        wTourUtils.assertPathName('/shop/payment', 'button[name=o_payment_submit_button]'),

        wsTourUtils.goToCart({quantity: 4, backend: false}),
        wsTourUtils.assertCartContains({productName: 'Acoustic Bloc Screens'}),
        wsTourUtils.assertCartContains({productName: 'Conference Chair (Steel)'}),
        wsTourUtils.assertCartContains({productName: 'Conference Chair (Aluminium)'}),
>>>>>>> a16f18081d2f74fcc38c1ebc72c1614001ed25de
    ],
);
