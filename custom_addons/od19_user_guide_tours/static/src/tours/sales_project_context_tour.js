import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Sales Project Context Tour
 *
 * Walks the user through the project dimension added to the Sales app:
 *  1. Open the Projects list from the Sales navbar
 *  2. Open a quotation and fill Project / Sale Mode / Project Owner
 *  3. Reach the Cost & Profit Analysis smart button
 */
registry.category("web_tour.tours").add("od19_sales_project_context_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("Let's link a <b>sales order</b> to its <b>project</b>."))
        ),

        // --- Projects entry in the Sales navbar ---
        {
            trigger: navSection("Projects"),
            content: markup(_t("Open the <b>Projects</b> menu (Sales ▸ Projects).")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Projects"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "These are the delivery projects a sales order can be attached to. " +
                "Each project carries its own <b>customer</b> and <b>project owner</b>."
            )),
        },

        // --- Attach a quotation to a project ---
        {
            trigger: navSection("Orders"),
            content: markup(_t("Now open the <b>Orders</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Quotations"),
            content: markup(_t("Open the <b>Quotations</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Quotations"),
        {
            trigger: ".o_list_renderer .o_data_row:first .o_data_cell:first",
            content: markup(_t("Open a quotation.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_project_id']",
            content: markup(_t(
                "The <b>Project</b> field links the order to its delivery project. " +
                "<b>Sale Mode</b> and <b>Project Owner</b> sit right next to it."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='od19_project_owner_id']",
            content: markup(_t(
                "The <b>Project Owner</b> is the person accountable for the project margin."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_form_view",
            content: markup(_t(
                "Once a project is set, a <b>Cost &amp; Profit Analysis</b> smart button appears " +
                "in the button box: it compares the order revenue with the analytic costs."
            )),
            tooltipPosition: "bottom",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t("Sales Project Context tour complete!")),
            run: "click",
        },
    ],
});
