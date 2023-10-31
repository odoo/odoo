odoo.define('purchase_stock.purchase_steps', function (require) {
"use strict";

var core = require('web.core');

var _t = core._t;
var PurchaseAdditionalTourSteps = require('purchase.purchase_steps');

PurchaseAdditionalTourSteps.include({

    init: function() {
        this._super.apply(this, arguments);
    },

    _get_purchase_stock_steps: function () {
        this._super.apply(this, arguments);
        return [{
            trigger: ".oe_button_box button[name='action_view_picking']",
            extra_trigger: ".oe_button_box button[name='action_view_picking']",
            content: _t("Receive the ordered products."),
            position: "bottom",
            run: 'click',
        }, {
            trigger: ".o_statusbar_buttons button[name='button_validate']",
            content: _t("Validate the receipt of all ordered products."),
            position: "bottom",
            run: 'click',
        }, {
            trigger: ".modal-footer .btn-primary",
            extra_trigger: ".modal-dialog",
            content: _t("Process all the receipt quantities."),
            position: "bottom",
        }, {
            trigger: ".o_back_button a, .breadcrumb-item:not('.active'):last",
            content: _t('Go back to the purchase order to generate the vendor bill.'),
            position: 'bottom',
        }, {
            trigger: ".o_statusbar_buttons button[name='action_create_invoice']",
            content: _t("Generate the draft vendor bill."),
            position: "bottom",
            run: 'click',
        }
        ];
    }
});

return PurchaseAdditionalTourSteps;

});
