/** @odoo-module **/

import Class from "@web/legacy/js/core/class";

var PurchaseAdditionalTourSteps = Class.extend({
    _get_purchase_stock_steps: function () {
        return [
            {
                auto: true, // Useless final step to trigger congratulation message
                trigger: ".o_purchase_order",
            },
        ];
    },
});

export default PurchaseAdditionalTourSteps;
