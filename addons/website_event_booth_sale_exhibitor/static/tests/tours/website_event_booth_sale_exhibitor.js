odoo.define("website_event_booth_sale_exhibitor.tour", function (require) {
    "use strict";

    var FinalSteps = require('website_event_booth_exhibitor.tour_steps');

    FinalSteps.include({

        _getSteps: function () {
            return [{
                content: 'Confirm your order',
                trigger: '.btn-primary[href="/shop/confirm_order"]',
                run: 'click',
            }, {
                content: 'Pay your order',
                trigger: '.btn-primary[name="o_payment_submit_button"]',
                run: 'click',
            }, {
                trigger: 'h3:contains("Please use the following transfer details")',
                run: function () {},
            }]
        }

    });

});