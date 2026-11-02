import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Doubtful Debt Tour
 *
 * Walks the user through the doubtful-debt (หนี้สงสัยจะสูญ) module:
 *  1. Accounting > Customers > หนี้สงสัยจะสูญ (Doubtful Debt)
 *  2. Provision (ตั้งค่าเผื่อหนี้สงสัยจะสูญ) and Write-off (ตัดหนี้สูญ)
 *  3. Configuration > ช่วงอายุหนี้ (Aging Buckets)
 */
registry.category("web_tour.tours").add("od19_doubtful_debt_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's review <b>Doubtful Debt</b> (หนี้สงสัยจะสูญ)."))
        ),
        {
            trigger: navSection("Customers"),
            content: markup(_t("Open the <b>Customers</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('หนี้สงสัยจะสูญ (Doubtful Debt)')",
            content: markup(_t("Open the <b>หนี้สงสัยจะสูญ (Doubtful Debt)</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- Provision (ตั้งค่าเผื่อหนี้สงสัยจะสูญ) ---
        {
            trigger: navItem("ตั้งค่าเผื่อหนี้สงสัยจะสูญ"),
            content: markup(_t("Open <b>ตั้งค่าเผื่อหนี้สงสัยจะสูญ</b> (provisions).")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("ตั้งค่าเผื่อหนี้สงสัยจะสูญ (Provisions)"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each provision groups the open receivables by aging bucket and computes " +
                "the allowance to book."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to create a provision.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            content: markup(_t(
                "Set the <b>date</b>, the <b>journal</b> and the provision lines. " +
                "Use <b>Compute</b> to fill the aging buckets automatically."
            )),
            run: "click",
        },
        {
            trigger: ".o_form_statusbar",
            content: markup(_t(
                "Workflow: <b>Compute</b> → <b>Post</b>. Posting creates the allowance " +
                "journal entry; the <b>Journal Entry</b> button opens it."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_notebook .nav-link:text('Provision Lines')",
            content: markup(_t(
                "The <b>Provision Lines</b> tab lists the customers, the open balance and " +
                "the computed provision amount."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Write-off (ตัดหนี้สูญ) ---
        {
            trigger: navSection("Customers"),
            content: markup(_t("Reopen the <b>Customers</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('หนี้สงสัยจะสูญ (Doubtful Debt)')",
            content: markup(_t("Open <b>หนี้สงสัยจะสูญ (Doubtful Debt)</b> again.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("ตัดหนี้สูญ"),
            content: markup(_t("Open <b>ตัดหนี้สูญ</b> (write-offs).")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("ตัดหนี้สูญ (Write-offs)"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Write-offs follow <b>Draft → Approved → Write Off</b>: only an accounting " +
                "manager can approve, and posting creates the expense entry."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- Aging buckets (Configuration) ---
        {
            trigger: navSection("Configuration"),
            content: markup(_t("Open the <b>Configuration</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("ช่วงอายุหนี้ (Aging Buckets)"),
            content: markup(_t(
                "Open <b>ช่วงอายุหนี้ (Aging Buckets)</b> to define the aging ranges and " +
                "the provision rate applied to each bucket."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("ช่วงอายุหนี้ (Aging Buckets)"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Doubtful Debt tour complete! Tune the aging buckets once and every " +
                "provision is computed consistently."
            )),
            run: "click",
        },
    ],
});
