    import { changePricelist, checkPriceCart } from "@website_event_sale/../tests/tours/helpers/WebsiteEventSaleTourMethods";

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
                trigger: `h5.card-title span:contains(${eventName})`,
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
           ...changePricelist(pricelistName),
           ...checkPriceSteps,
           ...checkPriceCart(priceCart),
        ]
    }
    export default { getPriceListChecksSteps }
