import { _t } from "@web/core/l10n/translation";

import PurchaseAdditionalTourSteps from "@purchase/js/tours/purchase_steps";
import { patch } from "@web/core/utils/patch";

patch(PurchaseAdditionalTourSteps.prototype, {

    _get_purchase_stock_steps: function () {
        return [
            {
                trigger: ".o-form-buttonbox button[name='action_view_picking']",
            },
        {
            trigger: ".o-form-buttonbox button[name='action_view_picking']",
            content: _t("Receive the ordered products."),
            tooltipPosition: "bottom",
            run: 'click',
        }, {
            trigger: ".o_statusbar_buttons button[name='button_validate']",
            content: _t("Validate the receipt of all ordered products."),
            tooltipPosition: "bottom",
            run: 'click',
        }, 
        {
            trigger: ".modal-dialog",
        },
        {
            trigger: ".modal-footer .btn-primary",
            content: _t("Process all the receipt quantities."),
            tooltipPosition: "bottom",
            run: "click",
        }, {
            trigger: ".o_back_button a, .breadcrumb-item:not('.active'):last",
            content: _t('Go back to the purchase order to generate the vendor bill.'),
            tooltipPosition: 'bottom',
            run: "click",
        }, {
            trigger: ".o_statusbar_buttons button[name='action_create_invoice']",
            content: _t("Generate the draft vendor bill."),
            tooltipPosition: "bottom",
            run: 'click',
        }
        ];
    }
});

export default PurchaseAdditionalTourSteps;
