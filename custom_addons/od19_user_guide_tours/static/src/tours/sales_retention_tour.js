import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Sales Retention Tour
 *
 * Walks the user through sales retentions (เงินประกันผลงาน):
 *  1. Sales > Retentions (เงินประกันผลงาน)
 *  2. Retention Outstanding (ค้างคืน) — pivot + list analysis
 *  3. Create a retention and run the Hold / Release / Close workflow
 */
registry.category("web_tour.tours").add("od19_sales_retention_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("Let's track <b>Sales Retentions</b> (เงินประกันผลงาน)."))
        ),
        {
            trigger: navSection("Retentions (เงินประกันผลงาน)"),
            content: markup(_t("Open the <b>Retentions (เงินประกันผลงาน)</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Retention Outstanding (ค้างคืน)"),
            content: markup(_t("Open <b>Retention Outstanding (ค้างคืน)</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Retention Outstanding (ค้างคืน)"),
        {
            trigger: ".o_pivot_view, .o_graph_view, .o_list_view",
            content: markup(_t(
                "This report shows every retention still <b>held</b>, grouped for analysis. " +
                "Use the view switcher to change between pivot, list and form."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_cp_switch_buttons .o_switch_view.o_list",
            content: markup(_t("Switch to the <b>list</b> view.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Lines are <b>red</b> when overdue and <b>green</b> once released or closed."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to record a retention.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            content: markup(_t(
                "Link the <b>contract</b>, the <b>customer</b> and the <b>invoice</b>, then " +
                "set the retention rate or amount and the expected <b>release date</b>."
            )),
            run: "click",
        },
        {
            trigger: ".o_form_statusbar",
            content: markup(_t(
                "Workflow: <b>Hold</b> → <b>Release</b> → <b>Close</b>. Use " +
                "<b>Retention Receipt</b> to print the document and <b>Cancel</b> to " +
                "abort a draft."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Sales Retention tour complete! Keep the money held under control and " +
                "release it on time."
            )),
            run: "click",
        },
    ],
});
