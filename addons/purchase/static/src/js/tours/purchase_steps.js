/** @odoo-module alias=purchase.purchase_steps **/

import core from "web.core";

var PurchaseAdditionalTourSteps = core.Class.extend({
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
