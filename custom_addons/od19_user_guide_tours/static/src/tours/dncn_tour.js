import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Debit Note / Credit Note (DN/CN) Tour
 *
 * Walks the user through:
 *  1. Creating a Debit Note from a posted invoice
 *  2. Creating a Credit Note from a posted invoice
 *  3. Remastering an invoice (cancel + recreate)
 *  4. Setting DN/CN reasons
 */
registry.category("web_tour.tours").add("od19_dncn_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t(
                "Let's learn how to create <b>Debit Notes</b>, <b>Credit Notes</b>, " +
                "and <b>Remaster</b> invoices (Odoo 19 has no built-in DN)."
            ))
        ),

        // --- DN/CN Reasons ---
        {
            trigger: navSection("Configuration"),
            content: markup(_t("Open the <b>Configuration</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("DN/CN Reasons"),
            content: markup(_t(
                "Open <b>DN/CN Reasons</b> to define why a debit or credit note is issued."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("DN/CN Reasons"),
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new DN/CN reason."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the reason name (e.g. Price Adjustment)."),
            run: "edit Price Adjustment",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        // --- Create DN/CN from Invoice ---
        {
            trigger: navSection("Customers"),
            content: markup(_t("Open the <b>Customers</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Invoices"),
            content: markup(_t("Open <b>Invoices</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t("Open a <b>posted invoice</b>. DN/CN can only be created from posted invoices.")),
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Click <b>Debit Note</b> to increase the invoice amount (e.g. additional charges)."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t("Open the same posted invoice again.")),
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Click <b>Credit Note</b> to reduce or refund the invoice amount."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t("Open the same posted invoice again.")),
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Click <b>Remaster</b> to cancel and recreate the invoice with corrections " +
                "(keeps the audit trail)."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "DN/CN workflow complete! Use <b>Debit Note</b> to add charges, <b>Credit Note</b> " +
                "to reduce/refund, and <b>Remaster</b> to cancel and recreate an invoice. " +
                "Always set the <b>Reason</b> and add a <b>Remark</b> for audit purposes."
            )),
            run: "click",
        },
    ],
});
