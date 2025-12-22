/** @odoo-module **/

    import { changePricelist, checkPriceCart } from "@website_event_sale/../tests/tours/helpers/WebsiteEventSaleTourMethods";

    function checkPriceBooth(eventName, price, priceSelected) {
        return [
            {
                content: "Go to page Event",
                trigger: '.nav-link:contains("Event")',
                run: "click",
                expectUnloadPage: true,
            },
            {
                content: 'Open "Test Event Booths" event',
                trigger: `h5.card-title span:contains(${eventName})`,
                run: "click",
                expectUnloadPage: true,
            },
            {
                content: 'Go to "Get A Booth" page',
                trigger: 'li.nav-item a:has(span:contains("Get A Booth"))',
                run: "click",
                expectUnloadPage: true,
            },
            {
                content: 'Select the booth',
                trigger: ".o_wbooth_booths input[name=event_booth_ids]:not(:visible)",
                run: function () {
                    document.querySelector('.o_wbooth_booths input[name="event_booth_ids"]:nth-child(1)').click();
                },
            },
            {
                content: "Verify Price displayed",
                trigger: `.oe_currency_value:contains(${price})`,
            },
            {
                content: "Verify Price of selected booth",
                trigger: `div.o_wbooth_booth_total_price span.oe_currency_value:contains(${priceSelected})`,
            },
        ]
    }
    function checkPriceDiscountBooth(eventName, price, priceSelected, discount) {
        return [
            ...checkPriceBooth(eventName, price, priceSelected),
            {
                content: "Verify Price before discount",
                trigger: `del:contains(${discount})`,
            },
        ]
    }
    export const getPriceListChecksSteps = function ({pricelistName, eventName, price, priceSelected, priceCart, priceBeforeDiscount=false}) {
        const checkPriceSteps = priceBeforeDiscount ? checkPriceDiscountBooth(eventName, price, priceSelected, priceBeforeDiscount) : checkPriceBooth(eventName, price, priceSelected);
        return [
           ...changePricelist(pricelistName),
           ...checkPriceSteps,
           ...checkPriceCart(priceCart),
        ]
    }
    export default { getPriceListChecksSteps }
