import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Accounting Reporting Tour
 *
 * Walks the user through the accounting control surfaces added on top of the
 * standard reporting menu:
 *  1. Finance Control Board          - live accounting KPI dashboard
 *  2. Accounting Operational Closure - the period-end checklist
 */
registry.category("web_tour.tours").add("od19_accounting_reporting_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's explore the new <b>Accounting reporting</b> tools."))
        ),

        // --- Finance Control Board ---
        {
            trigger: navSection("Finance Control Board"),
            content: markup(_t("Open the <b>Finance Control Board</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".od19-dashboard",
            timeout: 30000,
            content: markup(_t(
                "The board tracks <b>receivables</b>, <b>payables</b>, <b>tax</b> and the " +
                "<b>closing status</b> of the period in a single screen."
            )),
            tooltipPosition: "bottom",
        },

        // --- Accounting Operational Closure ---
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Accounting Operational Closure"),
            content: markup(_t("Open <b>Accounting Operational Closure</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Accounting Operational Closure"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each line is a closure <b>metric</b> with the number of open items and their " +
                "total amount — the go/no-go signal to clear before locking the period."
            )),
            run: "click",
        },
    ],
});
