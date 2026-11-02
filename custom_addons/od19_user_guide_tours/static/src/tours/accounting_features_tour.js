import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Accounting Features Tour
 *
 * Walks the user through:
 *  1. Withholding Tax (WHT) on vendor payments (type, rate, base, amount)
 *  2. Payer / Payee partner fields on prepayments
 *  3. BOT (Revenue Department) smart button, Actual Due Date and
 *     cancel reason on invoices
 *  4. Thai WHT PDF reports: ภงด.1 / ภงด.3 / ภงด.53 / ภงด.53 ทริส
 */
registry.category("web_tour.tours").add("od19_accounting_features_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t(
                "Let's explore the extra <b>Accounting</b> features: WHT on payments, " +
                "payer/payee, BOT lookup and Thai WHT reports."
            ))
        ),

        // --- WHT on Vendor Payment ---
        {
            trigger: ".o_menu_sections .dropdown-toggle:text('Vendors'), .o_menu_sections .o_nav_entry:text('Vendors')",
            content: markup(_t("Open the <b>Vendors</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-item:text('Payments'), .dropdown-menu .dropdown-item:contains('Payments')",
            content: markup(_t(
                "Open <b>Payments</b> to record a vendor payment with <b>Withholding Tax</b>."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new payment."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: _t("Select the vendor."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='amount'] input",
            content: _t("Enter the payment amount."),
            run: "edit 10000",
        },
        {
            trigger: ".o_field_widget[name='od19_wht_type_id'] input",
            content: markup(_t("Choose the <b>WHT Type</b> from the Thai withholding tax types.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_wht_rate'] .o_select_menu_toggler",
            content: markup(_t("Set the <b>WHT Rate</b> (1%, 1.5%, 2%, 3% or 5%).")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_wht_invoice_amount']",
            content: markup(_t(
                "The <b>WHT Base Amount</b> and <b>WHT Amount</b> are computed automatically " +
                "from the base and the rate."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_payer_id'] input",
            content: markup(_t(
                "Optionally set the <b>ผู้จ่ายเงิน / Payer</b> and <b>ผู้รับเงิน / Payee</b> partners."
            )),
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Invoices: BOT, Actual Due Date, Cancel Reason ---
        {
            trigger: ".o_menu_sections .dropdown-toggle:text('Customers'), .o_menu_sections .o_nav_entry:text('Customers')",
            content: markup(_t("Open the <b>Customers</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-item:text('Invoices'), .dropdown-menu .dropdown-item:contains('Invoices')",
            content: markup(_t("Open <b>Invoices</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "On an invoice you will find the <b>BOT</b> smart button (Revenue Department " +
                "tax invoice lookup) and the <b>Actual Due Date</b> (invoice date + 30 days)."
            )),
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "When you <b>Cancel</b> an invoice the system asks for a <b>cancel reason</b>, " +
                "which is stored and displayed on the form for audit."
            )),
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Thai WHT certificate reports (ภงด.1 / ภงด.3 / ภงด.53 / ภงด.53 ทริส) are available " +
                "from the <b>Print</b> menu on any payment."
            )),
            run: "click",
        },
    ],
});
