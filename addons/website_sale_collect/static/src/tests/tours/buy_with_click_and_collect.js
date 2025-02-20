import {registry} from '@web/core/registry';
import {clickOnElement} from '@website/js/tours/tour_utils';
import * as tourUtils from '@website_sale/js/tours/tour_utils';

registry.category('web_tour.tours').add('website_sale_collect_buy_product', {
    url: '/shop',
    checkDelay: 50,
    steps: () => [
        ...tourUtils.searchProduct("Test CAC Product"),
        clickOnElement("Test Product", 'a:contains("Test CAC Product")'),
        clickOnElement("Open Location selector", '.o_click_and_collect_availability'),
        clickOnElement("Choose location", '#submit_location_large'),
        clickOnElement('Add to cart', '#add_to_cart'),
        tourUtils.goToCart({quantity: 1}),
        tourUtils.goToCheckout(),
        {
            content: "Fill delivery address form",
            trigger: 'select[name="country_id"]',
            run: 'selectByLabel Belgium',
        },
        {
            trigger: 'input[name="name"]',
            run: 'edit Name',
        },
        {
            trigger: 'input[name="phone"]',
            run: 'edit 99999999',
        },
        {
            trigger: 'input[name="email"]',
            run: 'edit test@odoo.com',
        },
        {
            trigger: 'input[name="street"]',
            run: 'edit Test Street',
        },
        {
            trigger: 'input[name="city"]',
            run: 'edit Test City',
        },
        {
            trigger: 'input[name="zip"]',
            run: 'edit 10000',
        },
        {
            content: "Click on next button",
            trigger: '.oe_cart .btn:contains("Continue checkout")',
            run: 'click',
        },
        {
            content: "Ensure in store delivery method is selected.",
            trigger: 'input[name="o_delivery_radio"][data-delivery-type="in_store"]:checked',
        },
        {
            content: "Check the pickup address is set.",
            trigger: 'b[name="o_pickup_location_name"]:contains("Shop 1")',
        },
        tourUtils.confirmOrder(),
        {
            content: "Select `Pay on site`  payment method",
            trigger: 'input[name="o_payment_radio"][data-payment-method-code="pay_on_site"]',
            run: 'click',
        },
        tourUtils.pay(),
        {
            content: "Check payment status confirmation window",
            trigger: '.oe_website_sale_tx_status[data-order-tracking-info]',
        },
    ],
});
