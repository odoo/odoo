/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

import PurchaseAdditionalTourSteps from "@purchase/js/tours/purchase_steps";
import { patch } from "@web/core/utils/patch";

patch(PurchaseAdditionalTourSteps.prototype, {

    _get_purchase_stock_steps: function () {
        return [{
            trigger: ".o-form-buttonbox button[name='action_view_picking']",
            extra_trigger: ".o-form-buttonbox button[name='action_view_picking']",
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

export default PurchaseAdditionalTourSteps;
