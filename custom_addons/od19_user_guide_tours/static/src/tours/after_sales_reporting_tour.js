import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 After-Sales Reporting Tour
 *
 * Walks the user through the after-sales analytics that live under
 * Sales > After-Sales Reporting:
 *  1. After-Sales Dashboard - the control board
 *  2. Service Tickets KPI   - the underlying pivot analysis
 */
registry.category("web_tour.tours").add("od19_after_sales_reporting_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("Let's explore the <b>After-Sales reporting</b> suite."))
        ),

        // --- After-Sales Dashboard ---
        {
            trigger: navSection("After-Sales Reporting"),
            content: markup(_t("Open the <b>After-Sales Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("After-Sales Dashboard"),
            content: markup(_t("Open the <b>After-Sales Dashboard</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".od19-dashboard",
            timeout: 30000,
            content: markup(_t(
                "The dashboard summarises <b>service tickets</b>, <b>warranty claims</b>, " +
                "<b>SLA breaches</b> and <b>customer satisfaction</b> in one screen."
            )),
            tooltipPosition: "bottom",
        },

        // --- Service Tickets KPI ---
        {
            trigger: navSection("After-Sales Reporting"),
            content: markup(_t("Re-open <b>After-Sales Reporting</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Service Tickets"),
            content: markup(_t("Open the <b>Service Tickets</b> KPI.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Service Tickets KPI"),
        {
            trigger: ".o_pivot_view, .o_graph_view, .o_list_view",
            content: markup(_t(
                "The KPI opens as a <b>pivot</b>; use the view switcher to turn it into a " +
                "graph or a list and slice tickets by <b>team</b>, <b>type</b> or <b>stage</b>. " +
                "The same pattern drives the Warranty, Service Card, Returns, QC and " +
                "Customer Satisfaction KPIs."
            )),
            run: "click",
        },
    ],
});
