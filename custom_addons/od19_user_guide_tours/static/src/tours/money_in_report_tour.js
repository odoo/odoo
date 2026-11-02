import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Money In Analysis Report Tour
 *
 * Walks the user through:
 *  1. Generating a Money In report with filters
 *  2. Understanding the two phases (invoice-based vs cash-based)
 *  3. Reviewing report runs and analysis lines
 */
registry.category("web_tour.tours").add("od19_money_in_report_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's generate a <b>Money In Analysis</b> report."))
        ),

        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Money In Analysis')",
            content: markup(_t("Open <b>Money In Analysis</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Generate Report"),
            content: markup(_t("Click <b>Generate Report</b> to open the report wizard.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='date_from'] .o_input",
            content: _t("Set the start date of the analysis period."),
        },
        {
            trigger: ".o_field_widget[name='date_to'] .o_input",
            content: _t("Set the end date of the analysis period."),
        },
        {
            trigger: ".o_field_widget[name='phase'] .o_select_menu_toggler",
            content: markup(_t(
                "Choose the <b>phase</b>:<br/>" +
                "<b>Phase 1</b> (Invoice-based): recognizes revenue when invoices are posted.<br/>" +
                "<b>Phase 2</b> (Cash &amp; Invoice-based): recognizes revenue when cash is actually received."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='job_type_values'] .o_select_menu_toggler",
            content: markup(_t("Filter by <b>job type</b> (optional).")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_ids'] input",
            content: markup(_t("Filter by specific <b>customers</b> (leave blank for all).")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='salesperson_ids'] input",
            content: markup(_t("Filter by <b>salespersons</b> (optional).")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='project_ids'] input",
            content: markup(_t("Filter by <b>projects</b> (optional).")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='product_categ_ids'] input",
            content: markup(_t("Filter by <b>product categories</b> (optional).")),
            run: "click",
        },
        {
            trigger: "button[name='action_generate_report']",
            content: markup(_t("Click <b>Generate Report</b> to run the analysis.")),
            tooltipPosition: "left",
            run: "click",
        },
        // When no analysis line matches the filters, the wizard raises a
        // UserError and leaves both itself and the error dialog open, which
        // blocks the navbar. Close them before moving on. These steps must be
        // unconditional: the error dialog opens asynchronously right after the
        // click above, so an isActive guard would be evaluated before it
        // renders and skip the step permanently.
        {
            trigger: ".o_error_dialog .modal-footer .o-default-button",
            content: markup(_t("Close the warning dialog.")),
            tooltipPosition: "left",
            run: "click",
            timeout: 20000,
        },
        {
            trigger: ".o_dialog .modal-footer .btn-secondary",
            content: markup(_t("Close the report wizard.")),
            tooltipPosition: "left",
            run: "click",
            timeout: 20000,
        },

        // --- Review Report Runs ---
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Money In Analysis')",
            content: markup(_t("Open <b>Money In Analysis</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Report Runs"),
            content: markup(_t("Open <b>Report Runs</b> to see all generated reports.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            // Odoo 19 opens a record when a `td.o_data_cell` is clicked; the
            // `tr.o_data_row` itself is not clickable.
            trigger: ".o_list_renderer .o_data_row:first .o_data_cell:first",
            content: markup(_t("Open a report run to review the results.")),
            run: "click",
            // A run is only persisted when analysis lines are produced; when
            // the wizard raised a UserError no run exists and the list is empty.
            isActive: [".o_list_renderer .o_data_row"],
        },
        ...stepUtils.discardForm(),

        // --- Analysis Lines ---
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Money In Analysis')",
            content: markup(_t("Open <b>Money In Analysis</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Analysis Lines"),
            content: markup(_t(
                "Open <b>Analysis Lines</b> to see the detailed breakdown of revenue " +
                "by customer, salesperson, project, and product category."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Money In Analysis complete! Use <b>Phase 1</b> for invoice-based revenue " +
                "recognition and <b>Phase 2</b> for cash-based. Review <b>Report Runs</b> for " +
                "summary results and <b>Analysis Lines</b> for detailed breakdowns."
            )),
            run: "click",
        },
    ],
});
