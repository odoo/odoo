odoo.define('website_event_sale.tour.WebsiteEventSaleTourMethods', function (require) {
    'use strict';

    function changePricelist(pricelistName) {
        return [
            {
                content: "Go to page Shop",
                trigger: '.nav-link:contains("Shop")',
            },
            {
                content: "Toggle Pricelist",
                trigger: "div.o_pricelist_dropdown a[data-toggle=dropdown]",
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
                content: "Verify Price",
                trigger: `.oe_currency_value:contains(${price})`,
                run: function () {}, // it's a check
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
    function checkPriceCart(price) {
        return [
            {
                content: "Go to page Cart",
                trigger: '.fa-shopping-cart',
            },
            {
                content: "Verify Price",
                trigger: `#order_total td:contains(${price})`,
                run: function () {}, // it's a check
            },
        ]
    }
    const getPriceListChecksSteps = function ({pricelistName, eventName, price, priceBeforeDiscount=false}) {
        const checkPriceSteps = priceBeforeDiscount ? checkPriceDiscountEvent(eventName, price, priceBeforeDiscount) : checkPriceEvent(eventName, price);
        return [
            ...changePricelist(pricelistName),
            ...checkPriceSteps,
            ...checkPriceCart(price),
        ]
    }
    return { getPriceListChecksSteps, changePricelist, checkPriceCart }
});
