odoo.define("website_sale.tour_shop_custom_attribute_value", function (require) {
    "use strict";

    var tour = require("web_tour.tour");

    tour.register("shop_custom_attribute_value", {
        url: "/shop?search=Customizable Desk",
        test: true,
    }, [{
        content: "click on Customizable Desk",
        trigger: '.oe_product_cart a:contains("Customizable Desk")',
    }, {
        trigger: 'li.js_attribute_value span:contains(Custom)',
        extra_trigger: 'li.js_attribute_value',
        run: 'click',
    }, {
        trigger: 'input.variant_custom_value',
        run: 'text Wood',
    }, {
        id: 'add_cart_step',
        trigger: 'a:contains(Add to Cart)',
        run: 'click',
    }, {
        trigger: 'span:contains(Custom: Wood)',
        extra_trigger: '#cart_products',
        run: function (){}, // check
    }]);
});
