odoo.define("website_sale.tour_shop_custom_attribute_value", function (require) {
    "use strict";

    const { registry } = require("@web/core/registry");
    const tourUtils = require('website_sale.tour_utils');

    registry.category("web_tour.tours").add("shop_custom_attribute_value", {
        url: "/shop?search=Customizable Desk",
        test: true,
        steps: [{
        content: "click on Customizable Desk",
        trigger: '.oe_product_cart a:contains("Customizable Desk (TEST)")',
    }, {
        trigger: 'li.js_attribute_value span:contains(Custom TEST)',
        extra_trigger: 'li.js_attribute_value',
        run: 'click',
    }, {
        trigger: 'input.variant_custom_value',
        run: 'text Wood',
    }, {
        id: 'add_cart_step',
        trigger: 'a:contains(ADD TO CART)',
        run: 'click',
    },
        tourUtils.goToCart(),
    {
        trigger: 'span:contains(Custom TEST: Wood)',
        extra_trigger: '#cart_products',
        run: function (){}, // check
    }]});
});
