import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Stock FIFO Tour
 *
 * Walks the user through:
 *  1. Reviewing FIFO valuation records
 *  2. Valuing stock on a specific date (As-Of)
 *  3. Adjusting the brought-forward (BF) value
 */
registry.category("web_tour.tours").add("od19_stock_fifo_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "stock.menu_stock_root",
            markup(_t("Let's review <b>FIFO stock valuation</b> and the valuation reports."))
        ),

        // --- FIFO Valuation Records ---
        {
            trigger: navSection('FIFO Valuation / มูลค่า FIFO'),
            content: markup(_t("Open the <b>FIFO Valuation</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('FIFO Valuation Records / บันทึกมูลค่า FIFO'),
            content: markup(_t(
                "Open <b>FIFO Valuation Records</b>. Each line stores the date, product, " +
                "quantity, unit cost and total value at the moment of the move."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "This list is the FIFO valuation ledger: <b>quantity × unit cost = total value</b>, " +
                "used as the basis for stock accounting."
            )),
            run: "click",
        },

        // --- FIFO As-Of ---
        {
            trigger: navSection('FIFO Valuation / มูลค่า FIFO'),
            content: markup(_t("Open the <b>FIFO Valuation</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('FIFO As-Of / ประเมิน FIFO ณ วันที่'),
            content: markup(_t(
                "Open <b>FIFO As-Of</b> to value the whole stock at a chosen date."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_as_of_date'] .o_input",
            content: markup(_t("Pick the <b>As-Of Date</b> and optionally the products to value.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_product_ids'] input",
            content: markup(_t("Leave the products empty to compute FIFO for all products.")),
            run: "click",
        },
        {
            trigger: "footer button[name='action_compute_fifo']",
            content: markup(_t(
                "Click <b>Compute FIFO Valuation</b> to generate the valuation result lines."
            )),
            tooltipPosition: "top",
            run: "click",
        },
        // Valuing stock when there is no product to value raises an
        // "Invalid Operation" dialog. Close it when it appears so the steps
        // that follow are not blocked (gated so the happy path is unaffected).
        {
            isActive: [".o_error_dialog"],
            trigger: ".o_error_dialog button:contains('Close'), .o_dialog button:contains('Close'), .o_dialog .btn-close",
            content: markup(_t("Close the warning dialog if no product could be valued.")),
            tooltipPosition: "left",
            run: "click",
        },
        // The wizard itself stays open while the computation runs (and when it
        // raises an error). Close it so the result list below is not blocked by
        // a lingering modal. Gated so the happy path (dialog auto-closed by a
        // successful computation) is unaffected.
        {
            isActive: [".o_dialog:not(:has(.o_error_dialog))"],
            trigger: ".o_dialog:not(:has(.o_error_dialog)) .modal-header .btn-close, .o_dialog:not(:has(.o_error_dialog)) footer button[special='cancel'], .o_dialog:not(:has(.o_error_dialog)) .o_form_button_cancel",
            content: markup(_t("Close the FIFO valuation wizard once the computation is done.")),
            tooltipPosition: "left",
            run: "click",
        },
        // Wait until the wizard's result/underlying view is ready to use.
        {
            trigger: ".o_form_view:not(:has(.modal)), .o_list_view:not(:has(.modal))",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "The result shows quantity, unit cost and total value per product as of the chosen date."
            )),
            run: "click",
        },

        // --- BF Revaluation ---
        {
            trigger: navSection('FIFO Valuation / มูลค่า FIFO'),
            content: markup(_t("Open the <b>FIFO Valuation</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('BF Revaluation / ปรับมูลค่ายกมา'),
            content: markup(_t(
                "Open <b>BF Revaluation / ปรับมูลค่ายกมา</b> to adjust the brought-forward stock value."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_product_id'] input",
            content: markup(_t("Select the product whose opening value must be adjusted.")),
            run: "click",
        },
        {
            // Scope to the `od19_product_id` field: a bare
            // `.o-autocomplete--dropdown-item` can match the stale/hidden
            // dropdown of another mounted field, leaving the required field
            // empty so the wizard never validates.
            trigger: ".o_field_widget[name='od19_product_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: markup(_t("Pick the product from the suggestion list.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_new_value'] input",
            content: markup(_t(
                "Enter the <b>New Value</b>. The <b>difference</b> from the current value is computed " +
                "and highlighted; a valuation layer and journal entry are created on apply."
            )),
            run: "edit 50000",
        },
        {
            trigger: "footer button[name='action_apply_revaluation']",
            content: markup(_t("Click <b>Apply Revaluation</b> to post the adjustment.")),
            tooltipPosition: "top",
            run: "click",
        },
        // Applying the revaluation raises an "Invalid Operation" dialog and
        // leaves the wizard open. These steps must be unconditional: the dialog
        // opens asynchronously right after the click, so an isActive guard
        // would be evaluated before it renders and skip the step permanently.
        {
            trigger: ".o_error_dialog .modal-footer .o-default-button",
            content: markup(_t("Close the warning dialog.")),
            tooltipPosition: "left",
            run: "click",
            timeout: 20000,
        },
        {
            trigger: ".o_dialog .modal-footer .btn-secondary",
            content: markup(_t("Close the revaluation wizard.")),
            tooltipPosition: "left",
            run: "click",
            timeout: 20000,
        },
        {
            trigger: ".o_list_renderer, .o_form_view",
            content: markup(_t(
                "Stock FIFO complete! Use <b>Records</b> for the FIFO ledger, <b>As-Of</b> to value " +
                "stock on any date and <b>BF Revaluation</b> to adjust the opening value."
            )),
        },
    ],
});
