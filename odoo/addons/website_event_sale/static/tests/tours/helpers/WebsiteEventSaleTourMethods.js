/** @odoo-module **/
import wsTourUtils from '@website_sale/js/tours/tour_utils';

export function changePricelist(pricelistName) {
    return [
        {
            content: "Go to page Shop",
            trigger: '.nav-link:contains("Shop")',
        },
        {
            content: "Toggle Pricelist",
            trigger: '.o_pricelist_dropdown > .dropdown-toggle',
            run: 'click',
        },
        {
            content: `Activate Pricelist ${pricelistName}`,
            trigger: `.dropdown-item:contains(${pricelistName})`,
            run: 'click',
        },
        {
            content: 'Wait for pricelist to load',
            trigger: `.dropdown-toggle:contains(${pricelistName})`,
            run: function () {},
        },
    ];
}
function checkPriceEvent(eventName, price) {
    return [
        {
            content: "Go to page Event",
            trigger: '.nav-link:contains("Event")',
        },
        {
            content: "Open the Pycon event",
            trigger: `.o_wevent_events_list a:contains(${eventName})`,
        },
        {
            content: "Open the ticket picking modal",
            trigger: `button:contains("Register")`,
        },
        {
            content: "Verify Price",
            trigger: `.oe_currency_value:contains(${price})`,
            run: function () {}, // it's a check
        },
        {
            content: "Open the ticket picking modal",
            trigger: `.modal-content button:contains("Close")`,
        },
    ]
}
function checkPriceDiscountEvent(eventName, price, discount) {
    return [
        ...checkPriceEvent(eventName, price),
        {
            content: "Verify Price before discount",
            trigger: `del:contains(${discount})`,
            run: function () {}, // it's a check
        },
    ]
}
export function checkPriceCart(price) {
    return [
        wsTourUtils.goToCart(),
        ...wsTourUtils.assertCartAmounts({total: price}),
    ]
}
export const getPriceListChecksSteps = function ({pricelistName, eventName, price, priceBeforeDiscount=false}) {
    const checkPriceSteps = priceBeforeDiscount ? checkPriceDiscountEvent(eventName, price, priceBeforeDiscount) : checkPriceEvent(eventName, price);
    return [
        ...changePricelist(pricelistName),
        ...checkPriceSteps,
        ...checkPriceCart(price),
    ]
}
export default { getPriceListChecksSteps, changePricelist, checkPriceCart }
