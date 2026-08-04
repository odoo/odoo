import { _t } from "@web/core/l10n/translation";

import PurchaseAdditionalTourSteps from "@purchase/js/tours/purchase_steps";
import { patch } from "@web/core/utils/patch";

patch(PurchaseAdditionalTourSteps.prototype, {

    _get_purchase_stock_steps: function () {
        return [
            {
                isActive: ["desktop"],
                trigger: ".o-form-buttonbox button[name='action_view_picking']",
            },
        {
            isActive: ["mobile", "body:has(.o-form-buttonbox .o_button_more)"],
            trigger: ".o-form-buttonbox .o_button_more",
            run: "click",
        },
        {
            trigger: "button[name='action_view_picking']",
            content: _t("Receive the ordered products."),
            run: 'click',
        }, {
            trigger: ".o_statusbar_buttons button[name='button_validate']",
            content: _t("Validate the receipt of all ordered products."),
            run: 'click',
        }, 
        {
            isActive: ["body:has(.modal-footer .btn-primary)"],
            trigger: ".modal-footer .btn-primary",
            content: _t("Process all the receipt quantities."),
            run: "click",
        }, {
            isActive: ["desktop"],
            trigger: ".o_statusbar_status .o_arrow_button_current:contains('Done')",
        }, {
            isActive: ["mobile"],
            trigger: ".o_statusbar_status button.dropdown-toggle:contains('Done')",
        }, {
            trigger: ".o_back_button",
            content: _t('Go back to the purchase order to generate the vendor bill.'),
            run: "click",
        }, {
            isActive: ["auto", "mobile"],
            trigger: ".o_statusbar_buttons",
            async run({ queryFirst, click }) {
                const buttonOutsideDropdownMenu = queryFirst("button:enabled:contains('Upload Bill')");
                const node = queryFirst(".o_statusbar_buttons button:has([data-icon='more_vert'])");
                if (!buttonOutsideDropdownMenu && node) {
                    await click(node);
                }
            },
        }, {
            isActive: ["auto"],
            trigger: "button:contains('Upload Bill')",
            content: _t("Generate the draft vendor bill."),
            async run({ inputFiles }) {
                const files = [new File(["hello, world"], "bill.txt", { type: "text/plain" })];
                await inputFiles(".document_file_uploader", files);
            },
        }, {
            isActive: ["manual"],
            trigger: "button:contains('Upload Bill')",
            content: _t("Generate the draft vendor bill."),
            run: "click",
        }
        ];
    }
});

export default PurchaseAdditionalTourSteps;
