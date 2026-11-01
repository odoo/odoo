import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Asset Loan Tour
 *
 * Walks the user through:
 *  1. Creating an Asset Loan record
 *  2. Adding equipment lines
 *  3. Confirming the loan
 *  4. Returning the equipment
 *  5. Marking equipment as lost (if applicable)
 */
registry.category("web_tour.tours").add("od19_asset_loan_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "maintenance.menu_maintenance_title",
            markup(_t("Let's manage <b>Asset Loans</b> for equipment borrowing and returns."))
        ),

        {
            trigger: navSection("Configuration"),
            content: markup(_t("Open the <b>Configuration</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Asset Loan')",
            content: markup(_t("Open <b>Asset Loan</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Loans"),
            content: markup(_t("Open <b>Loans</b> to view and create asset loans.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new asset loan."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            // A plain click on an empty Many2one input does not always open the
            // dropdown; typing a term is what triggers the search and renders
            // the options list.
            trigger: ".o_field_widget[name='borrower_id'] input",
            content: _t("Search for the borrower (employee or partner)."),
            run: "edit a",
        },
        {
            // The "Loading..." placeholder is rendered as a sibling <li> that
            // ALSO carries the o-autocomplete--dropdown-item class, so a bare
            // selector clicks it and the typed text is never committed. Real
            // option rows are the only ones with `d-block`; "Create ..." /
            // "Search More..." rows carry o_m2o_dropdown_option.
            trigger: ".o-autocomplete--dropdown-item.d-block:not(.o_m2o_dropdown_option)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='loan_date'] .o_input",
            content: _t("Open the date picker to set the loan date."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='loan_date'] input.o_input",
            content: _t("Set the loan date."),
            run: "edit 2026-01-15",
        },
        {
            trigger: ".o_field_widget[name='expected_return_date'] .o_input",
            content: _t("Set the expected return date."),
            run: "edit 2026-02-15",
        },
        {
            trigger: "a.nav-link:contains('Equipment')",
            content: markup(_t(
                "Open the <b>Equipment</b> page to add the items being loaned."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='line_ids'] .o_field_x2many_list_row_add a",
            content: _t("Add an equipment line."),
            run: "click",
        },
        {
            trigger: ".o_selected_row .o_field_widget[name='equipment_id'] input",
            content: _t("Search for the equipment to loan."),
            run: "edit OD19 Tour Equipment",
        },
        {
            trigger: ".o_selected_row .o_field_widget[name='equipment_id'] .o_m2o_dropdown_option_create",
            content: markup(_t(
                "Pick <b>Create ...</b> so the tour always borrows a brand new piece of " +
                "equipment: an item that is already on loan cannot be borrowed twice."
            )),
            run: "click",
        },
        {
            trigger: ".o_selected_row .o_field_widget[name='quantity'] input",
            content: _t("Set the quantity to loan."),
            run: "edit 1",
        },
        {
            trigger: ".o_control_panel .o_form_button_save:visible",
            content: _t("Save the loan."),
            run: "click",
        },
        // Saving may be rejected by a constraint (e.g. double borrow). Wait for
        // either outcome first: a wait step is never blocked by a modal.
        {
            trigger: ".o_error_dialog, .o_form_readonly, .o_form_saved",
        },
        {
            isActive: [".o_error_dialog"],
            trigger: ".o_error_dialog .modal-footer .o-default-button",
            content: markup(_t("Close the warning dialog.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            // Only act on a saved record: header buttons on an unsaved form
            // would save it again and could raise the same constraint.
            isActive: [".o_form_readonly", "button[name='action_confirm']"],
            trigger: "button[name='action_confirm']",
            content: markup(_t(
                "Click <b>Confirm</b> to mark the equipment as borrowed."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            isActive: ["button[name='action_return']"],
            trigger: "button[name='action_return']",
            content: markup(_t(
                "When the equipment is returned, click <b>Return</b>. " +
                "The returned quantity is updated on each line."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            isActive: ["button[name='action_lost']"],
            trigger: "button[name='action_lost']",
            content: markup(_t(
                "If equipment is not returned, click <b>Mark Lost</b> to record the loss."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            isActive: ["button.o_back_button"],
            trigger: "button.o_back_button",
            content: _t("Go back to the loans list."),
            run: "click",
        },
        {
            trigger: ".o_list_renderer, .o_form_view",
            content: markup(_t(
                "Asset Loan workflow complete: <b>Create → Confirm → Return</b> (or <b>Mark Lost</b>). " +
                "Use the <b>Overdue</b> filter to find loans past their expected return date."
            )),
        },
    ],
});
