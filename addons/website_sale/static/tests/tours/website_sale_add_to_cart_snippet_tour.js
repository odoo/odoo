/** @odoo-module **/

import wsTourUtils from '@website_sale/js/tours/tour_utils';
import wTourUtils from '@website/js/tours/tour_utils';

function editAddToCartSnippet() {
    return [
        ...wTourUtils.clickOnEditAndWaitEditMode(),
        ...wTourUtils.clickOnSnippet({id: 's_add_to_cart'})
    ]
}

wTourUtils.registerWebsitePreviewTour('add_to_cart_snippet_tour', {
        url: '/',
        edition: true,
        test: true,
    },
    () => [
        ...wTourUtils.dragNDrop({name: 'Add to Cart Button'}),

        // Basic product with no variants
        ...wTourUtils.clickOnSnippet({id: 's_add_to_cart'}),
        ...wTourUtils.selectElementInWeSelectWidget('product_template_picker_opt', 'Pedal Bin', true),
        ...wTourUtils.clickOnSave(),
        wTourUtils.clickOnElement('add to cart button', ':iframe .s_add_to_cart_btn'),
        {
            trigger: ":iframe nav li.o_wsale_my_cart sup:contains(1)",
            run: () => null,
        },
        // Product with 2 variants with visitor choice (will open modal)
        ...editAddToCartSnippet(),
        ...wTourUtils.selectElementInWeSelectWidget('product_template_picker_opt', 'Conference Chair', true),
        ...wTourUtils.clickOnSave(),
        wTourUtils.clickOnElement('add to cart button', ':iframe .s_add_to_cart_btn'),
        wTourUtils.clickOnElement('continue shopping', ':iframe span:contains(Continue Shopping)'),
        {
            trigger: "body:not(:has(.modal))",
            run: () => null,
        },
        {
            trigger: ":iframe nav li.o_wsale_my_cart sup:contains(2)",
            run: () => null,
        },

        // Product with 2 variants with a variant selected
        ...editAddToCartSnippet(),
        ...wTourUtils.selectElementInWeSelectWidget('product_template_picker_opt', 'Conference Chair', true),
        ...wTourUtils.selectElementInWeSelectWidget('product_variant_picker_opt', 'Conference Chair (Aluminium)'),
        ...wTourUtils.clickOnSave(),
        wTourUtils.clickOnElement('add to cart button', ':iframe .s_add_to_cart_btn'),

        // Basic product with no variants and action=buy now
        ...editAddToCartSnippet(),
<<<<<<< saas-17.4
        ...wTourUtils.selectElementInWeSelectWidget('product_template_picker_opt', 'Pedal Bin', true),
||||||| 1b8a73f1700a7623394d7de44eaef5133cea676a
        ...wTourUtils.selectElementInWeSelectWidget('product_template_picker_opt', 'Acoustic Bloc Screens', true),
=======
        ...wTourUtils.selectElementInWeSelectWidget('product_template_picker_opt', 'Acoustic Bloc Screens', true),
        {
            trigger: `we-select[data-name=action_picker_opt] we-toggler:contains("Add to Cart")`,
            run: () => null,
        },
>>>>>>> a15485cfac05b4aac6c05bc539f361fc553dff87
        ...wTourUtils.selectElementInWeSelectWidget('action_picker_opt', 'Buy Now'),
        ...wTourUtils.clickOnSave(),
        wTourUtils.clickOnElement('add to cart button', ':iframe .s_add_to_cart_btn'),
        {
            // wait for the page to load, as the next check was sometimes too fast
            content: "Wait for the redirection to the payment page",
<<<<<<< saas-17.4
            trigger: 'body',
||||||| 1b8a73f1700a7623394d7de44eaef5133cea676a
            trigger: 'body',
            isCheck: true,  // wait for the page to load, as the next check was sometimes too fast
=======
            trigger: "iframe h3:contains('Confirm order')",
            timeout: 20000,
            run: () => null,
>>>>>>> a15485cfac05b4aac6c05bc539f361fc553dff87
        },
        wTourUtils.assertPathName('/shop/payment', ':iframe a[href="/shop/cart"]'),

        wsTourUtils.goToCart({quantity: 4, backend: true}),
        wsTourUtils.assertCartContains({productName: 'Pedal Bin', backend: true}),
        wsTourUtils.assertCartContains({productName: 'Conference Chair (Steel)', backend: true}),
        wsTourUtils.assertCartContains({productName: 'Conference Chair (Aluminium)', backend: true}),
    ],
);
