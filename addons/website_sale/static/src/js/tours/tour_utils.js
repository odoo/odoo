odoo.define("website_sale.tour_utils", function (require) {
    "use strict";
    
    const core = require("web.core");
    const _t = core._t;


    function goToCart(quantity = 1, position = "bottom") {
        return {
            content: _t("Go to cart"),
            trigger: `a:has(.my_cart_quantity:containsExact(${quantity}))`,
            position: position,
            run: "click",
        };
    }

    return {
        goToCart,
    };
});
