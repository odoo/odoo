import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Fleet Accounting Tour
 *
 * Walks the user through:
 *  1. Setting up vehicle expense categories
 *  2. Recording vehicle service/expense logs
 *  3. Linking expenses to analytic accounts and departments
 *  4. Tracking vehicle costs by project / department
 */
registry.category("web_tour.tours").add("od19_fleet_accounting_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "fleet.menu_root",
            markup(_t("Let's manage <b>Fleet Accounting</b>: vehicle expenses and cost tracking."))
        ),

        // --- Expense Categories ---
        {
            trigger: ".o_menu_sections .dropdown-toggle:text('Fleet')",
            content: markup(_t("Open the <b>Fleet</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-item:text('Expense Categories')",
            content: markup(_t(
                "Open <b>Expense Categories</b> to classify vehicle costs (fuel, maintenance, etc.)."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new expense category."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the category name (e.g. Fuel)."),
            run: "edit Fuel",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        // --- Vehicle Service Log ---
        {
            trigger: ".o_menu_sections .dropdown-toggle:text('Fleet')",
            content: markup(_t("Open the <b>Fleet</b> menu again.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-item:text('Fleet')",
            content: markup(_t("Go back to the <b>Fleet</b> vehicle list.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_switch_view.o_list",
            content: markup(_t(
                "Switch to the <b>list view</b>. An empty database shows read-only sample " +
                "kanban cards, so we create a fresh vehicle to set its accounting information."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Create a new vehicle to classify its costs.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='model_id'] input",
            content: markup(_t("Select the vehicle <b>Model</b> (the only required field).")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='model_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("Pick the model from the suggestion list."),
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_field_widget[name='expense_category_id'] input",
            content: markup(_t(
                "Set the <b>Expense Category</b> for proper cost classification."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='department_id'] input",
            content: markup(_t(
                "Set the <b>Department</b> to allocate the cost to the right team."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='analytic_account_id'] input",
            content: markup(_t(
                "Set the <b>Analytic Account</b> (Job Number) to track vehicle costs by project."
            )),
            run: "click",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        {
            trigger: ".o_kanban_view, .o_list_view",
            content: markup(_t(
                "Fleet Accounting complete! Vehicle expenses are now classified by <b>category</b>, " +
                "<b>department</b>, and <b>analytic account</b> (project), enabling accurate P&amp;L tracking."
            )),
            run: "click",
        },
    ],
});
