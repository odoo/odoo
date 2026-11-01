import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Custom Dashboards Tour
 *
 * Walks the user through the OD19 dashboard builder that lives inside the
 * Dashboards application:
 *  1. Open the Custom Dashboards section
 *  2. Declare a data source and its available fields
 *  3. Open the dashboard viewer / builder
 *  4. Create a new dashboard from the viewer
 */
registry.category("web_tour.tours").add("od19_dashboard_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "spreadsheet_dashboard.spreadsheet_dashboard_menu_root",
            markup(_t("Let's build a <b>custom dashboard</b> for the owner."))
        ),

        {
            trigger: navSection("Custom Dashboards"),
            content: markup(_t("Open the <b>Custom Dashboards</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Data Sources"),
            content: markup(_t("Start with <b>Data Sources</b>: they describe which model is queried.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Data Sources"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t("Each row exposes one Odoo model to the dashboard widgets.")),
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to declare a data source.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: markup(_t("Give the source a readable <b>name</b>.")),
            run: "edit Sales Orders",
        },
        {
            trigger: ".o_field_widget[name='model_name'] input",
            content: markup(_t(
                "Enter the technical <b>model</b> to query, e.g. <i>sale.order</i> or " +
                "<i>account.move</i>. The model name must be unique."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='field_ids']",
            content: markup(_t(
                "In <b>Available Fields</b> list the fields widgets may use, and tag each " +
                "one as a <b>measure</b>, a <b>group by</b> or a <b>date</b>."
            )),
            tooltipPosition: "top",
        },
        ...stepUtils.discardForm(),

        // --- Dashboard viewer / builder ---
        {
            trigger: navSection("Custom Dashboards"),
            content: markup(_t("Reopen the <b>Custom Dashboards</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("My Dashboards"),
            content: markup(_t("Open <b>My Dashboards</b>, the viewer itself.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".od19-dashboard",
            timeout: 30000,
            content: markup(_t(
                "This is the dashboard viewer. Pick a dashboard and a period in the " +
                "toolbar, and hit <b>Refresh data</b> to reload the KPIs."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".od19-dashboard__toolbar .od19-text-btn[title='Create a dashboard']",
            content: markup(_t("Click <b>New</b> to create your own dashboard.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".od19-new-dashboard #od19_dash_name",
            content: markup(_t("Name the dashboard, e.g. Owner Executive Dashboard (Tour).")),
            run: "edit Owner Executive Dashboard (Tour)",
        },
        {
            isActive: [".od19-new-dashboard .btn-primary"],
            trigger: ".od19-new-dashboard .btn-primary",
            content: markup(_t("Click <b>Create</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".od19-dashboard__body",
            timeout: 30000,
            content: markup(_t(
                "The dashboard is created. Switch to <b>Customize</b> (design mode) to add " +
                "a KPI, bar, line, pie or list widget from a data source, then drag and " +
                "resize the widgets on the grid."
            )),
        },
        {
            trigger: ".od19-dashboard__title",
            content: markup(_t(
                "Custom Dashboards complete! Declare a data source → open My Dashboards → " +
                "<b>New</b> dashboard → <b>Customize</b> → add widgets. " +
                "Use <b>Configuration &gt; Dashboards</b> to manage visibility and audience."
            )),
            run: "click",
        },
    ],
});
