odoo.define("website_sale_delivery.website_sale_tour", function (require) {
"use strict";
/**
 * Add custom steps to handle the optional products modal introduced
 * by the product configurator module.
 */
var tour = require('web_tour.tour');
require('website_sale.tour');
var website_sale = require('website_sale.website_sale');

website_sale.include({
    _onChangeCartQuantity(event) {
        super._onChangeCartQuantity.apply(this, event);
        $('body').attr('rpc-done', 1);
    },
});


var addCartStepIndex = _.findIndex(tour.tours.shop_buy_product.steps, function (step) {
    return (step.id === 'set one');
});

tour.tours.shop_buy_product.steps.splice(addCartStepIndex + 1, 0,         {
            content: "wait for delivery race condition",
            trigger: 'body[view-event-id]',
            run: () => {
                const $body = $('body');
                $body.removeAttr('rpc-done');
            }
});

});
