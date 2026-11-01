import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Jasper Reporting Tour
 *
 * Walks the user through the JasperReports foundation shipped with
 * `od19_reporting_jasper`:
 *
 *  1. Report Templates           - QWeb / JasperServer template registry
 *  2. Report Actions             - bind a template to a print action
 *  3. Jasper Database Connection - the JDBC connection used by JasperStarter
 *
 * Everything lives under Accounting > Configuration > Reports.
 */
registry.category("web_tour.tours").add("od19_jasper_report_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t(
                "Let's explore the <b>Jasper Reports</b> foundation " +
                "(Accounting > Configuration > Reports)."
            ))
        ),

        // --- Report Templates ---
        {
            trigger: navSection("Configuration"),
            content: markup(_t("Open the <b>Configuration</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Report Templates"),
            content: markup(_t(
                "Open <b>Report Templates</b>: the registry of every QWeb and " +
                "JasperServer report template."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        // Opening a menu entry switches the action asynchronously: the previous
        // view stays mounted for a few frames. Without this guard the two steps
        // below match the *previous* list and its "New" button, which gets
        // disabled by `executeButtonCallback()` and then reused (still disabled)
        // by the real list, so the form never opens.
        waitForAction("Report Templates"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each template lists its <b>name</b>, the target <b>model</b>, the " +
                "<b>report type</b> (QWeb or JasperServer) and whether it is still <b>active</b>."
            )),
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to register a report template.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            content: markup(_t(
                "Pick the <b>Model</b> the report is built on and the <b>Report Type</b>. " +
                "Choosing <b>JasperServer</b> reveals an extra <b>JasperServer URL</b> field."
            )),
            run: "click",
        },
        {
            trigger: ".o_notebook .nav-link:contains('Template')",
            content: markup(_t(
                "On the <b>Template</b> tab you paste the QWeb XML template (or the " +
                "JasperServer report reference) with the built-in XML editor."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Report Actions ---
        {
            trigger: navSection("Configuration"),
            content: markup(_t("Re-open the <b>Configuration</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Report Actions"),
            content: markup(_t(
                "Open <b>Report Actions</b> to bind a template to a print action, so the " +
                "report can be printed straight from a record's form."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "A report action stores the <b>template</b>, the <b>model</b> and the output " +
                "<b>format</b>, and is exposed as a <b>Print</b> entry on matching records."
            )),
            run: "click",
        },

        // --- Jasper Database Connection ---
        {
            trigger: navSection("Configuration"),
            content: markup(_t("Re-open the <b>Configuration</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Jasper Database Connection"),
            content: markup(_t(
                "Open <b>Jasper Database Connection</b>: JasperReports reads the Odoo data " +
                "over JDBC."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "The connection holds <b>host</b>, <b>port</b>, <b>database</b> and <b>user</b>. " +
                "Defaults are taken from <i>odoo.conf</i>, and the <b>Role Creation Script</b> tab " +
                "renders the SQL needed for a dedicated read-only role."
            )),
            run: "click",
        },
    ],
});
