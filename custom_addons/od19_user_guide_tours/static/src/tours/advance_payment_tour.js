import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Advance Payments Tour
 *
 * Walks the user through:
 *  1. Creating a customer or supplier advance payment
 *  2. Posting the advance
 *  3. Reconciling the advance against invoices
 *  4. Cancelling and resetting advances
 */
registry.category("web_tour.tours").add("od19_advance_payment_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's manage <b>Advance Payments</b> (customer deposits and supplier prepayments)."))
        ),

        {
            trigger: navSection("Advance Payments"),
            content: markup(_t("Open the <b>Advance Payments</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new advance payment."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='advance_type'] .o_select_menu_toggler",
            content: markup(_t(
                "Choose the <b>advance type</b>: Customer (deposit received) or Supplier (prepayment made)."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: _t("Select the customer or supplier."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='amount'] input",
            content: _t("Enter the advance amount."),
            run: "edit 20000",
        },
        {
            trigger: ".o_field_widget[name='journal_id'] input",
            content: _t("Select the payment journal (bank or cash)."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='journal_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='advance_account_id'] input",
            content: markup(_t(
                "Set the <b>advance account</b> (a current liability or asset account)."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='advance_account_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='date'] .o_input",
            content: _t("Set the payment date."),
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_post']",
            content: markup(_t(
                "Click <b>Post</b> to record the advance payment in the accounting system."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            // The stage buttons inside the statusbar are disabled until the
            // state actually changes, so target the always-enabled statusbar
            // container instead of the disabled `button[data-value=...]`.
            trigger: ".o_statusbar_status",
            content: markup(_t(
                "Once the advance is <b>posted</b>, it can be reconciled against invoices. " +
                "The status changes to <b>Reconciled</b> automatically when the full amount is used."
            )),
            tooltipPosition: "top",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Advance Payments workflow: <b>Draft → Post → Reconciled</b>. " +
                "Use <b>Cancel</b> to void an advance and <b>Reset to Draft</b> to reuse it. " +
                "Remaining balance is tracked automatically as the advance is applied to invoices."
            )),
            run: "click",
        },
    ],
});
