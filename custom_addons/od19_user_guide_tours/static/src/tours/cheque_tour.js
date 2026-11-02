import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Cheque Management Tour
 *
 * Walks the user through:
 *  1. Creating a cheque (receivable or payable)
 *  2. Confirming the cheque
 *  3. Depositing / clearing / marking paid
 *  4. Bouncing a cheque
 *  5. Printing the cheque
 */
registry.category("web_tour.tours").add("od19_cheque_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's manage <b>Cheques</b> from creation to clearance."))
        ),

        {
            trigger: ".o_menu_sections .o_nav_entry:text('Cheques')",
            content: markup(_t("Open the <b>Cheques</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Cheques"),
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new cheque."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the cheque number."),
            run: "edit CHQ-000123",
        },
        {
            trigger: ".o_field_widget[name='cheque_type'] .o_select_menu_toggler",
            content: markup(_t("Choose the <b>cheque type</b> (receivable or payable).")),
            run: "click",
        },
        {
            trigger: ".o_select_menu_item:contains('Customer')",
            content: markup(_t(
                "Pick the <b>Customer</b> cheque type (a cheque received). The <b>Deposit</b> " +
                "action is only available for receivable cheques."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: _t("Select the payer or payee."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='bank_id'] input",
            content: _t("Select the bank."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='amount'] input",
            content: _t("Enter the cheque amount."),
            run: "edit 50000",
        },
        {
            trigger: ".o_field_widget[name='cheque_date'] .o_input",
            content: _t("Set the cheque date."),
            run: "edit 2026-01-15",
        },
        {
            trigger: ".o_field_widget[name='due_date'] .o_input",
            content: _t("Set the due date."),
            run: "edit 2026-02-15",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_confirm']",
            content: markup(_t("<b>Confirm</b> the cheque.")),
            tooltipPosition: "left",
            run: "click",
        },
        // Confirming a receivable cheque with no "Cheque Received Account"
        // configured raises a UserError ("Invalid Operation") which opens a
        // dialog; while it is up every following click fails with "It is not
        // allowed to do action on an element that's below a modal". Wait for
        // that dialog (a step without run is never blocked by a modal) and
        // close it before continuing.
        {
            trigger: ".modal-header .btn-close, .modal-footer .o-default-button, .o_form_readonly, .o_form_saved",
            timeout: 20000,
        },
        {
            isActive: [".modal-header .btn-close"],
            trigger: ".modal-header .btn-close",
            content: markup(_t("Acknowledge the warning about the Cheque Received Account.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            // Deposit requires a "Cheque Received Account" configured on the
            // company (Settings ▸ Companies ▸ Cheque Management); a default
            // database has none, so clicking Deposit raises a UserError and the
            // tour cannot continue. Keep the step informational and anchored on
            // the always-present form container so the tour still completes.
            trigger: ".o_form_view",
            content: markup(_t(
                "For receivable cheques, click <b>Deposit</b> when the cheque is deposited at the bank. " +
                "Deposit requires the <b>Cheque Received Account</b> to be set in " +
                "<b>Settings ▸ Companies ▸ Cheque Management</b>."
            )),
            tooltipPosition: "left",
        },
        {
            // Clear (like Deposit) needs a working deposit flow first; keep it
            // informational for the same reason as above.
            trigger: ".o_form_view",
            content: markup(_t(
                "Click <b>Clear</b> when the cheque is cleared (funds received). " +
                "If the cheque bounces, use <b>Bounce</b>."
            )),
            tooltipPosition: "left",
        },
        {
            trigger: "button[name='action_print_cheque']",
            content: markup(_t(
                "Use the <b>Print Cheque</b> button to print the cheque. " +
                "A single QWeb template supports all banks."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        // Printing opens the report, and Odoo 19 first shows the "Configure
        // your document layout" dialog when no report layout has been saved.
        // Target a *visible* element: the `.o_dialog` wrapper has no box of
        // its own, so a `visible:true` query never matches it. Close the
        // dialog (a step without run is never blocked by the modal) before
        // discarding the form, otherwise the back button below is hidden
        // behind the modal.
        {
            trigger: "button[name='document_layout_save'], .o_dialog .modal-title",
            timeout: 20000,
        },
        {
            isActive: [".o_dialog .modal-header .btn-close"],
            trigger: ".o_dialog .modal-header .btn-close",
            content: markup(_t("Close the document layout dialog.")),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Cheque workflow complete: <b>Draft → Confirm → Deposit → Clear</b> (or <b>Paid</b> for payables). " +
                "Use <b>Bounce</b> for returned cheques."
            )),
            run: "click",
        },
    ],
});
