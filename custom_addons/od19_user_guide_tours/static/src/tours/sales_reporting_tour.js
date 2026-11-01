import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Sales Reporting Tour
 *
 * Walks the user through the project-oriented sales reports that live under
 * Sales > Reporting:
 *  1. Project Revenue - revenue and order count per project
 *  2. Repeat Business - customers who order again within a period
 */
registry.category("web_tour.tours").add("od19_sales_reporting_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("Let's explore the new <b>Sales reporting</b> views."))
        ),

        // --- Project Revenue ---
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Project Revenue"),
            content: markup(_t("Open <b>Project Revenue</b>: revenue booked per project.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Project Revenue Overview"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each line groups the confirmed orders of one <b>project</b> with its " +
                "<b>commercial customer</b>, <b>project owner</b>, <b>order count</b> and " +
                "<b>untaxed amount</b>."
            )),
        },

        // --- Repeat Business ---
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Re-open <b>Reporting</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Repeat Business"),
            content: markup(_t("Open <b>Repeat Business</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Repeat Business"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Repeat Business highlights the customers who order again within the period — " +
                "use it to measure retention and spot loyal accounts."
            )),
            run: "click",
        },
    ],
});
