import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Sales Contract & Billing Tour
 *
 * Walks the user through:
 *  1. Creating a Sales Contract (master contract with limit amount)
 *  2. Setting the over-limit consumption policy
 *  3. Creating a Sales Order under the contract
 *  4. Attaching Billing Evidence (delivery / service report)
 *  5. Checking billing readiness
 */
registry.category("web_tour.tours").add("od19_sales_contract_billing_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("Let's explore the <b>Sales</b> module: Contracts, Orders, and Billing Evidence."))
        ),
        // --- Sales Contract ---
        {
            trigger: navSection('Sales Contracts'),
            content: markup(_t("Open the <b>Sales Contracts</b> menu to create a master contract.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        // "Sales Contracts" is a top-level section that directly opens an
        // action. Switching actions is asynchronous (the previous view stays
        // mounted for a few frames), so `.o_list_button_add` would click the
        // *Quotations* list's "New" button and open a sale order instead of a
        // contract. Wait for the target action breadcrumb first.
        waitForAction('Sales Contracts'),
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new Sales Contract."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the contract name (e.g. Project A Master Contract)."),
            run: "edit Project A Master Contract",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: _t("Select or create the commercial customer."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("Pick the customer from the suggestion list."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_project_id'] input",
            content: markup(_t(
                "Link the contract to a <b>Project</b> (Job No). Each contract belongs to one project."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_project_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("Pick the project from the suggestion list."),
            run: "click",
        },
        // The Project field is required: when no project matches, picking a
        // suggestion opens a "Create Project" dialog (the full project form) whose
        // Name **and** Job Number are required. Fill both then save, otherwise the
        // dialog stays open on a validation error and blocks every field below.
        {
            isActive: [".o_dialog .o_field_widget[name='name'] input"],
            trigger: ".o_dialog .o_field_widget[name='name'] input",
            content: markup(_t("Name the <b>Project</b> created from the contract.")),
            run: `edit Contract Project ${Date.now()}`,
        },
        {
            isActive: [".o_dialog .o_field_widget[name='job_no'] input"],
            trigger: ".o_dialog .o_field_widget[name='job_no'] input",
            content: markup(_t(
                "Set the <b>Job Number</b> of the new project (required and unique)."
            )),
            run: `edit JOB-${Date.now()}`,
        },
        {
            isActive: [".o_dialog .o_form_button_save, .o_dialog footer .btn-primary"],
            trigger: ".o_dialog .o_form_button_save, .o_dialog footer .btn-primary",
            content: markup(_t("Save the <b>Project</b> created from the contract.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "body:not(:has(.o_dialog .o_form_view))",
        },
        {
            trigger: ".o_field_widget[name='limit_amount'] input",
            content: markup(_t(
                "Set the <b>Limit Amount</b> (the committed budget for this contract)."
            )),
            run: "edit 1000000",
        },
        {
            trigger: ".o_field_widget[name='over_limit_policy'] .o_select_menu_toggler",
            content: markup(_t(
                "Choose the <b>Over-Limit Policy</b>: block, warn, or allow consumption beyond the limit."
            )),
            run: "click",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "a.nav-link:contains('Activities')",
            content: markup(_t(
                "Use the <b>Activities</b> page to add consumption lines that reduce the available limit."
            )),
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Billing Evidence (accessed from Sales Order) ---
        {
            trigger: navSection('Orders'),
            content: markup(_t("Open <b>Orders</b> to access Sales Orders.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            // "Orders" (action 338) filters on `search_default_sales`
            // ([('state','=','sale')]) and therefore shows only confirmed
            // orders. A fresh database has none, so the list is empty and Odoo
            // paints sample rows (REF0001…) that point at non-existent record
            // ids: clicking one raises "records with IDs 1 cannot be found" and
            // stays on the list. "Quotations" (action 339) uses
            // `search_default_my_quotation` and lists the real draft / sent
            // orders, so the following step can actually open a form.
            trigger: navItem('Quotations'),
            content: markup(_t("Open the <b>Quotations</b> list to access Sales Orders.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction('Quotations'),
        {
            // The record is opened by clicking a *cell*: Odoo 19 binds
            // `t-custom-click` on `td.o_data_cell`, not on `tr.o_data_row`,
            // so clicking the row itself does nothing.
            trigger: ".o_list_renderer .o_data_row:first .o_data_cell:first",
            content: markup(_t(
                "Open a <b>Sales Order</b>. Billing Evidence is attached from the Sales Order form " +
                "and tracks the <b>Billing Readiness State</b>."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_billing_readiness_state']",
            content: markup(_t(
                "The <b>Billing Readiness State</b> shows whether the order is ready to invoice " +
                "(Ordered → Worked → Evidenced → Ready to Bill → Billed). " +
                "Attach delivery slips or service reports as evidence before invoicing."
            )),
            run: "click",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Great! You now know how to set up a <b>Master Contract</b> with a consumption limit and " +
                "attach <b>Billing Evidence</b> before invoicing. The system tracks status from " +
                "<b>Ordered → Worked → Evidenced → Ready to Bill → Billed</b>."
            )),
            run: "click",
        },
    ],
});
