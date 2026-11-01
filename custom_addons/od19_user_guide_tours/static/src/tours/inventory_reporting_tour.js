import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Inventory Reporting Tour
 *
 * Walks the user through the warehouse reporting tools:
 *  1. Logistics Board   - live warehouse control dashboard
 *  2. Movement Backlog  - stock moves still waiting to be processed
 *  3. Inventory Accuracy - counted vs theoretical variances
 */
registry.category("web_tour.tours").add("od19_inventory_reporting_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "stock.menu_stock_root",
            markup(_t("Let's explore the new <b>Inventory reporting</b> tools."))
        ),

        // --- Logistics Board ---
        {
            trigger: navSection("Logistics Board"),
            content: markup(_t("Open the <b>Logistics Board</b>, the warehouse control dashboard.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".od19-dashboard",
            timeout: 30000,
            content: markup(_t(
                "The board aggregates inbound/outbound KPIs, the processing backlog and " +
                "SLA status in a single screen."
            )),
            tooltipPosition: "bottom",
        },

        // --- Movement Backlog ---
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Movement Backlog"),
            content: markup(_t(
                "Open <b>Movement Backlog</b>: the stock moves that are still waiting to be " +
                "processed."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Inventory Movement Backlog"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "The backlog lists every open move with its <b>product</b>, <b>location</b> and " +
                "<b>age</b>, so overdue transfers stand out."
            )),
        },

        // --- Inventory Accuracy ---
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Re-open <b>Reporting</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Inventory Accuracy"),
            content: markup(_t(
                "Open <b>Inventory Accuracy</b>: the variance between counted and theoretical " +
                "quantities."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Inventory Accuracy"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each line shows a counting <b>session</b>, its <b>location</b>, the number of " +
                "<b>lines</b> and the <b>variance lines</b> still to investigate."
            )),
            run: "click",
        },
    ],
});
