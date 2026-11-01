import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Project Enhanced Tour
 *
 * Walks the user through:
 *  1. Defining project types (hierarchical) for projects and tasks
 *  2. Reviewing the Project Risk Report (margin, overdue AR, risk score)
 */
registry.category("web_tour.tours").add("od19_project_enhanced_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "project.menu_main_pm",
            markup(_t("Let's configure <b>Project Types</b> and review the <b>Project Risk Report</b>."))
        ),

        // --- Project Types ---
        {
            trigger: navSection("Project Types"),
            content: markup(_t(
                "Open <b>Project Types</b> to define a classification used on projects and tasks."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new project type."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input, .o_field_widget[name='name'] textarea",
            content: _t("Enter the type name (e.g. Installation)."),
            run: "edit Installation",
        },
        {
            trigger: ".o_field_widget[name='parent_id'] input",
            content: markup(_t(
                "Optionally set a <b>Parent Type</b> to build a classification hierarchy."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='project_ok'] input",
            content: markup(_t(
                "Tick <b>Usable on Projects</b> and/or <b>Usable on Tasks</b> to control where the " +
                "type can be selected."
            )),
            run: "click",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        // --- Risk Report ---
        {
            trigger: navSection("Risk Report"),
            content: markup(_t(
                "Open the <b>Risk Report</b> to monitor project profitability and risk."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each project shows <b>contract amount</b>, <b>invoiced</b>, <b>actual cost</b>, " +
                "<b>committed cost</b>, <b>overdue AR</b> and the resulting <b>margin %</b>."
            )),
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "A <b>risk score</b> and <b>risk level</b> (high / medium / low) are computed so you can " +
                "act early on unprofitable projects."
            )),
            run: "click",
        },
    ],
});
