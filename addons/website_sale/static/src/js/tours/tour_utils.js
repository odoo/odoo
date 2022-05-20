odoo.define("website_sale.tour_utils", function (require) {
    "use strict";

    const core = require("web.core");
    const _t = core._t;


    function goToCart({quantity = 1, position = "bottom", backend = false} = {}) {
        return {
            content: _t("Go to cart"),
            trigger: `${backend ? "iframe" : ""} a:has(.my_cart_quantity:containsExact(${quantity}))`,
            position: position,
            run: "click",
        };
    }

    function assertCartContains(productName, backend = false) {
        return {
                content: `Checking if ${productName} is in the cart`,
                trigger: `${backend ? "iframe" : ""} a:contains(${productName})`,
            }
    }

    /**
     * Used to select a pricelist on the /shop view
     */
    function selectPriceList(pricelist) {
        return [
            {
                content: "Click on pricelist dropdown",
                trigger: "div.o_pricelist_dropdown a[data-toggle=dropdown]",
            },
            {
                content: "Click on pricelist",
                trigger: `span:contains(${pricelist})`,
            },
        ]
    }

    /**
     * Used to assert if the price attribute of a given product is correct on the /shop view
     */
    function assertProductPrice(attribute, value, productName) {
        return {
            content: `The ${attribute} of the ${productName} is ${value}`,
            trigger: `div:contains("${productName}") [data-oe-expression="template_price_vals[\'${attribute}\']"] .oe_currency_value:contains("${value}")`,
            run: () => {
            }
        }
    }

    return {
        assertCartContains,
        assertProductPrice,
        goToCart,
        selectPriceList,
    };
});
