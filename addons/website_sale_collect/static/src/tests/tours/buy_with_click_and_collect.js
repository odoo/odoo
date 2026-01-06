import { registry } from '@web/core/registry';
import { clickOnElement } from '@website/js/tours/tour_utils';
import * as tourUtils from '@website_sale/js/tours/tour_utils';

registry.category('web_tour.tours').add('website_sale_collect_widget', {
    steps: () => [
        ...tourUtils.searchProduct("Test CAC Product", { select: true }),
        {
            content: "Check standard delivery is not possible",
            trigger: '[name="delivery_availability"] div:contains("Not available")',
        },
        clickOnElement("Open Location selector", '[name="click_and_collect_availability"]'),
        {
            content: "Check the dialog is opened",
            trigger: '.o_location_selector',
        },
        clickOnElement("Choose location", '#submit_location_large'),
        {
            content: "Check pickup location is set",
            trigger: '[name="click_and_collect_availability"] div:contains("Shop 1")',
        },
        ...tourUtils.addToCartFromProductPage(),
        tourUtils.goToCart({ quantity: 1 }),
        tourUtils.goToCheckout(),
        ...tourUtils.fillAddressForm(),
        {
            content: "Check standard deliveries are marked as unavailable for the order",
            trigger: 'input[name="o_delivery_radio"][data-delivery-type="fixed"] ~ label:contains("Not available")',
        },
    ],
});

registry.category('web_tour.tours').add(
    'website_sale_collect_buy_product_default_location_pick_up_in_store',
    {
        steps: () => [
            ...tourUtils.searchProduct("Test CAC Product", { select: true }),
            ...tourUtils.addToCartFromProductPage(),
            tourUtils.goToCart(),
            tourUtils.goToCheckout(),
            ...tourUtils.fillAddressForm({
                name: "Name",
                phone: "99999999",
                email: "test@odoo.com",
                street: "Test Street",
                city: "Test City",
                zip: "10000",
            }),
            {
                content: "Ensure in store delivery method is selected.",
                trigger: 'input[name="o_delivery_radio"][data-delivery-type="in_store"]:checked',
            },
            {
                content: "Check the pickup address is set.",
                trigger: 'b[name="o_pickup_location_name"]:contains("Shop 1")',
            },
            {
                content: "Wait for delivery method RPC to complete",
                trigger: '[name="website_sale_main_button"]:not(.disabled):not([disabled])',
            },
            tourUtils.confirmOrder(),
            {
                content: "Select `Pay on site`  payment method",
                trigger: 'input[name="o_payment_radio"][data-payment-method-code="pay_on_site"]',
                run: 'click',
            },
            ...tourUtils.pay({ expectUnloadPage: true }),
            {
                content: "Check payment status confirmation window",
                trigger: '[name="order_confirmation"][data-order-tracking-info]',
            },
        ],
    });
