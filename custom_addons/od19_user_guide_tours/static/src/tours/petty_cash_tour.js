import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Petty Cash Tour
 *
 * Walks the user through petty cash (เงินทดรองจ่าย) of
 * od19_accounting_petty_cash:
 *  1. Accounting > Petty Cash > Transactions
 *  2. Review the transaction list and open a new transaction
 *  3. Run the Post / Reconcile workflow and the payment-certificate print
 *  4. Go back and open the petty cash Funds
 */
registry.category("web_tour.tours").add("od19_petty_cash_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's record <b>Petty Cash</b> (เงินทดรองจ่าย) expenses and replenishments."))
        ),
        {
            trigger: navSection("Petty Cash"),
            content: markup(_t("Open the <b>Petty Cash</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Transactions"),
            content: markup(_t("Open <b>Transactions</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Petty Cash Transactions"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Every expense paid out of a fund, and every <b>replenishment</b> paid back " +
                "into it, is listed here with its fund, amount and state."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to record a petty cash transaction.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            content: markup(_t(
                "Choose the <b>fund</b> and the <b>transaction type</b> (<b>Expense</b> or " +
                "<b>Replenishment</b>), then the expense account, the amount and the journal."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_document_type']",
            content: markup(_t(
                "In <b>เอกสารประกอบ / Document</b> pick the supporting document type. With " +
                "<b>Payment Certificate</b> you can also print the ใบรับรองแทนใบเสร็จ and mark " +
                "the VAT as creditable."
            )),
            run: "click",
        },
        {
            trigger: ".o_form_statusbar",
            content: markup(_t(
                "Workflow: <b>Post</b> creates the journal entry, then <b>Reconcile</b> clears " +
                "the fund. <b>Reset to Draft</b> reopens a cancelled transaction."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Petty cash funds ---
        {
            trigger: navSection("Petty Cash"),
            content: markup(_t("Reopen the <b>Petty Cash</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Funds"),
            content: markup(_t("Open <b>Funds</b> to manage the cash boxes.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Petty Cash Funds"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each <b>fund</b> is a cash box backed by an account. Deactivate a fund " +
                "instead of deleting it once it is closed."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Petty Cash tour complete! Keep every small expense receipted and the fund " +
                "balanced."
            )),
            run: "click",
        },
    ],
});
