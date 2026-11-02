import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Credit Gate Tour
 *
 * Walks the user through the customer credit-gate monitoring screens:
 *  1. Sales > Reporting > Credit Gate > Blocked Documents
 *  2. Sales > Reporting > Credit Gate > Credit Pending
 *
 * The sales order confirmation itself is still gated by
 * od19_sales_customer_risk_gate ("no credit approval, no confirmation").
 */
registry.category("web_tour.tours").add("od19_credit_gate_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("Let's review the <b>Credit Gate</b> (customer credit control)."))
        ),
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Credit Gate')",
            content: markup(_t("Open the <b>Credit Gate</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- Blocked documents ---
        {
            trigger: navItem("Blocked Documents"),
            content: markup(_t("Open <b>Blocked Documents</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Risk Gate Events"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Every line is a document that the credit gate stopped: the customer, the " +
                "reason code, the gate stage and the user who tried to confirm it."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- Pending credit reviews ---
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Reopen the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Credit Gate')",
            content: markup(_t("Open <b>Credit Gate</b> again.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Credit Pending"),
            content: markup(_t("Open <b>Credit Pending</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Credit Pending Customers"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Credit Gate tour complete! Customers waiting for a credit decision are " +
                "listed here — approve the credit before confirming their sales orders."
            )),
            run: "click",
        },
    ],
});
