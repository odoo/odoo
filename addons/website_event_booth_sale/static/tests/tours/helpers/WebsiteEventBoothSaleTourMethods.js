odoo.define('website_event_booth_sale.tour.WebsiteEventBoothSaleTourMethods', function (require) {
    'use strict';

    const { changePricelist, checkPriceCart } = require('website_event_sale.tour.WebsiteEventSaleTourMethods');

    function checkPriceBooth(eventName, price, priceSelected) {
        return [
            {
                content: "Go to page Event",
                trigger: '.nav-link:contains("Event")',
            },
            {
                content: 'Open "Test Event Booths" event',
                trigger: `h5.card-title span:contains(${eventName})`,
            },
            {
                content: 'Go to "Get A Booth" page',
                trigger: 'li.nav-item a:has(span:contains("Get A Booth"))',
            },
            {
                content: 'Select the booth',
                trigger: '.o_wbooth_booths input[name="event_booth_ids"]',
                run: function () {
                    $('.o_wbooth_booths input[name="event_booth_ids"]:lt(1)').click();
                },
            },
            {
                content: "Verify Price displayed",
                trigger: `.oe_currency_value:contains(${price})`,
                run: function () {}, // it's a check
            },
            {
                content: "Verify Price of selected booth",
                trigger: `div.o_wbooth_booth_total_price span.oe_currency_value:contains(${priceSelected})`,
                run: function () {}, // it's a check
            },
        ]
    }
    function checkPriceDiscountBooth(eventName, price, priceSelected, discount) {
        return [
            ...checkPriceBooth(eventName, price, priceSelected),
            {
                content: "Verify Price before discount",
                trigger: `del:contains(${discount})`,
                run: function () {}, // it's a check
            },
        ]
    }
    const getPriceListChecksSteps = function ({pricelistName, eventName, price, priceSelected, priceCart, priceBeforeDiscount=false}) {
        const checkPriceSteps = priceBeforeDiscount ? checkPriceDiscountBooth(eventName, price, priceSelected, priceBeforeDiscount) : checkPriceBooth(eventName, price, priceSelected);
        return [
           ...changePricelist(pricelistName),
           ...checkPriceSteps,
           ...checkPriceCart(priceCart),
        ]
    }
    return { getPriceListChecksSteps }
});
