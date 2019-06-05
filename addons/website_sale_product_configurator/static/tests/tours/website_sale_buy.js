odoo.define("website_sale_product_configurator.website_sale_tour", function (require) {
"use strict";
/**
 * Add custom steps to handle the optional products modal introduced
 * by the product configurator module.
 */
var tour = require('web_tour.tour');
require('website_sale.tour');

var addCartStepIndex = _.findIndex(tour.tours.shop_buy_product.steps, function (step) {
    return (step.id === 'add_cart_step');
});

tour.tours.shop_buy_product.steps.splice(addCartStepIndex + 1, 0, {
    content: "click in modal on 'Proceed to checkout' button",
    trigger: 'button:contains("Proceed to Checkout")',
});

});
