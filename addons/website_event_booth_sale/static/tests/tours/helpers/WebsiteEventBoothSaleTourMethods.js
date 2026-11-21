    import { checkPriceCart } from "@website_event_sale/../tests/tours/helpers/WebsiteEventSaleTourMethods";
    import * as wsTourUtils from "@website_sale/js/tours/tour_utils";

    function checkPriceBooth(eventName, price) {
        return [
            {
                content: "Go to page Event",
                trigger: '.nav-link:contains("Event")',
                run: "click",
                expectUnloadPage: true,
            },
            {
                content: 'Open "Test Event Booths" event',
                trigger: `h2.card-title span:contains(${eventName})`,
                run: "click",
                expectUnloadPage: true,
            },
            {
                content: 'Go to "Booth" page',
                trigger: 'a:contains("Become exhibitor")',
                run: "click",
                expectUnloadPage: true,
            },
            {
                content: "Check that the first booth is selected by default",
                trigger: ".o_wbooth_booths .form-check:first-child input[name=event_booth_ids]:not(:visible):checked",
            },
            {
                content: "Verify Price displayed",
                trigger: `.oe_currency_value:contains(${price})`,
            },
        ]
    }
    function checkPriceDiscountBooth(eventName, price, discount) {
        return [
            ...checkPriceBooth(eventName, price),
            {
                content: "Verify Price before discount",
                trigger: `del:contains(${discount})`,
            },
        ]
    }
    export const getPriceListChecksSteps = function ({pricelistName, eventName, price, priceCart, priceBeforeDiscount=false}) {
        const checkPriceSteps = priceBeforeDiscount ? checkPriceDiscountBooth(eventName, price, priceBeforeDiscount) : checkPriceBooth(eventName, price);
        return [
           ...wsTourUtils.selectPriceList(pricelistName),
           ...checkPriceSteps,
           ...checkPriceCart(priceCart),
        ]
    }
    export default { getPriceListChecksSteps }
