import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 HR Expense Tour
 *
 * Walks the user through:
 *  1. Creating an expense line
 *  2. Submitting the expense sheet
 *  3. Request Validation (tier validation: Dept Manager -> Accounting -> CEO)
 *  4. Marking as reimbursed
 *  5. Thai expense types and payment methods
 */
registry.category("web_tour.tours").add("od19_hr_expense_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "hr_expense.menu_hr_expense_root",
            markup(_t("Let's learn the <b>HR Expense</b> workflow with 3-level tier approval."))
        ),

        // --- Create Expense ---
        {
            trigger: ".o_menu_sections .dropdown-toggle:text('My Expenses')",
            content: markup(_t("Open the <b>My Expenses</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-item:text('My Expenses')",
            content: markup(_t("Open <b>My Expenses</b> to create a new expense.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new expense line."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the expense description."),
            run: "edit Client Visit - Transportation",
        },
        {
            trigger: ".o_field_widget[name='product_id'] input",
            content: _t("Select the expense product/category."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='product_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("Pick the first available expense category."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='quantity'] input",
            content: markup(_t(
                "Set the <b>quantity</b> (and unit price); the expense <b>total amount</b> is " +
                "computed automatically from both."
            )),
            run: "edit 1",
        },
        {
            trigger: ".o_field_widget[name='total_amount']",
            content: markup(_t(
                "The <b>total amount</b> is a computed, read-only field: quantity x unit price."
            )),
        },
        {
            trigger: ".o_field_widget[name='payment_mode'] .o_radio_input[data-value='own_account']",
            content: markup(_t(
                "Choose <b>Payment Mode</b>: own account (employee paid) or company account."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='payment_method'] .o_select_menu_toggler",
            content: markup(_t(
                "Set the <b>Payment Method</b> (cash, transfer, etc.)."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='thai_expense_type'] .o_select_menu_toggler",
            content: markup(_t(
                "Set the <b>Thai Expense Type</b> for tax and reporting classification."
            )),
            run: "click",
        },
        ...stepUtils.saveForm(),

        // --- Submit ---
        ...stepUtils.statusbarButtonsSteps(
            "Submit",
            markup(_t("Click <b>Submit</b> to send the expense for approval.")),
            ".o_form_view"
        ),

        // --- Tier Validation ---
        // เอกสารที่ต้องขออนุมัติจะแสดงปุ่ม "Request Validation"
        // (need_validation = True) หลัง Submit
        {
            isActive: ["button[name='request_validation']"],
            trigger: "button[name='request_validation']",
            content: markup(_t(
                "Click <b>Request Validation</b> to start the 3-level approval: " +
                "Department Manager → Accounting → CEO."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            isActive: ["button[name='validate_tier']"],
            trigger: "button[name='validate_tier']",
            content: markup(_t(
                "Each approver clicks <b>Validate</b> in their turn. " +
                "Approval follows the sequence and cannot be skipped."
            )),
            tooltipPosition: "left",
            run: "click",
        },

        // --- Mark Reimbursed ---
        {
            isActive: ["button[name='action_mark_reimbursed']"],
            trigger: "button[name='action_mark_reimbursed']",
            content: markup(_t(
                "For own-account expenses, click <b>Mark Reimbursed</b> once the employee has been paid."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        // Submitting or reimbursing can raise a "Confirmation" dialog (e.g. an
        // expense that duplicates an existing one). Acknowledge it first,
        // otherwise the discard/back buttons below are blocked by the modal.
        {
            isActive: [".modal-footer .btn-primary"],
            trigger: ".modal-footer .btn-primary",
            content: _t("Acknowledge the confirmation dialog."),
            tooltipPosition: "top",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "HR Expense workflow complete! The process is: <b>Create → Submit → " +
                "Request Validation → Validate ×3 → Approve → Reimbursed</b>. " +
                "Thai expense types and payment methods support local compliance."
            )),
            run: "click",
        },
    ],
});
