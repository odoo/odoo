odoo.define("website_event_booth_sale_exhibitor.tour", function (require) {
    "use strict";

    var FinalSteps = require('website_event_booth_exhibitor.tour_steps');

    FinalSteps.include({

        _getSteps: function () {
            return [{
                content: 'Checkout your order',
                trigger: 'a[role="button"] span:contains("Process Checkout")',
                run: 'click',
            }, {
                content: "Select `Wire Transfer` payment method",
                trigger: '#payment_method label:contains("Wire Transfer")',
            }, {
                content: "Pay",
                //Either there are multiple payment methods, and one is checked, either there is only one, and therefore there are no radio inputs
                // extra_trigger: '#payment_method input:checked,#payment_method:not(:has("input:radio:visible"))',
                trigger: 'button[name="o_payment_submit_button"]:visible:not(:disabled)',
            }, {
                content: "Last step",
                trigger: '.oe_website_sale_tx_status:contains("Please use the following transfer details")',
                timeout: 30000,
            }];
        }

    });

});
