import * as wsTourUtils from '@website_sale/js/tours/tour_utils';

const closeModal = {
    content: "Close the ticket picking modal",
    trigger: `.modal.modal_shown .modal-content button:contains("Close")`,
    run: "click",
};

export function changePricelist(pricelistName) {
    return [
        {
            content: "Go to page Shop",
            trigger: '.nav-link:contains("Shop")',
            run: "click",
            expectUnloadPage: true,
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
            expectUnloadPage: true,
        },
        {
            content: 'Wait for pricelist to load',
            trigger: `.dropdown-toggle:contains(${pricelistName})`,
        },
    ];
}
function checkPriceEvent(eventName, price, close = true) {
    const steps = [
        {
            content: "Go to page Event",
            trigger: '.nav-link:contains("Event")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Open the Pycon event",
            trigger: `.o_wevent_events_list a:contains(${eventName})`,
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Open the ticket picking modal",
            trigger: `button:contains("Register")`,
            run: "click",
        },
        {
            content: "Verify Price",
            trigger: `.oe_currency_value:contains(${price})`,
        },
    ];
    if (close) {
        steps.push(closeModal);
    }
    return steps;
}
function checkPriceDiscountEvent(eventName, price, discount) {
    return [
        ...checkPriceEvent(eventName, price, false),
        {
            content: "Verify Price before discount",
            trigger: `del:contains(${discount})`,
        },
        closeModal,
    ];
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
