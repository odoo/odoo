import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Asset Disposal Tour
 *
 * Walks the user through:
 *  1. Creating and validating a fixed asset
 *  2. Disposing the asset (generates a disposal journal entry)
 *  3. Recording disposal reason and linked documents
 *  4. Reverting a disposal
 */
registry.category("web_tour.tours").add("od19_asset_disposal_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's learn how to <b>dispose</b> a fixed asset and generate the disposal entry."))
        ),

        // --- Make sure an Asset Profile exists ---
        // Creating and validating an asset requires a profile, and a fresh
        // database has none. Create one first, otherwise the asset save fails
        // on the required `profile_id` and the tour gets stuck.
        {
            trigger: navSection("Configuration"),
            content: markup(_t(
                "An asset first needs an <b>Asset Profile</b>. Open the <b>Configuration</b> menu."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Asset Profiles"),
            content: markup(_t(
                "Open <b>Asset Profiles</b> (Configuration ▸ Assets ▸ Asset Profiles)."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new asset profile."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Name the profile (e.g. IT Equipment)."),
            run: "edit IT Equipment",
        },
        {
            trigger: ".o_field_widget[name='account_asset_id'] input",
            content: markup(_t("Select the <b>Asset Account</b> (the balance-sheet account of the asset).")),
            run: "click",
        },
        {
            // Scope the pick to this field's own dropdown: several hidden
            // autocomplete menus stay mounted, so an unscoped selector can hit
            // a stale menu and leave the required field empty.
            trigger: ".o_field_widget[name='account_asset_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='account_depreciation_id'] input",
            content: markup(_t("Select the <b>Depreciation Account</b> (accumulated depreciation).")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='account_depreciation_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='account_expense_depreciation_id'] input",
            content: markup(_t("Select the <b>Depreciation Expense Account</b>.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='account_expense_depreciation_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='account_residual_value_id'] input",
            content: markup(_t(
                "Select the <b>Residual Value Account</b>; the disposal entry needs it."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='account_residual_value_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='journal_id'] input",
            content: markup(_t("Select the journal used to post the asset entries.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='journal_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            run: "click",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        {
            trigger: navSection("Assets"),
            content: markup(_t("Open the <b>Assets</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Assets"),
            content: markup(_t("Open the <b>Assets</b> list.")),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- Create and validate an asset ---
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new fixed asset."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='profile_id'] input",
            content: markup(_t("Link the asset to the <b>IT Equipment</b> profile created above.")),
            run: "edit IT Equipment",
        },
        {
            trigger: ".o-autocomplete--dropdown-item:contains('IT Equipment')",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the asset name (e.g. Machine A)."),
            run: "edit Machine A",
        },
        {
            trigger: ".o_field_widget[name='purchase_value'] input",
            content: _t("Enter the purchase value."),
            run: "edit 120000",
        },
        {
            trigger: ".o_field_widget[name='salvage_value'] input",
            content: _t("Enter the salvage (residual) value."),
            run: "edit 12000",
        },
        {
            trigger: ".o_field_widget[name='date_start'] .o_input",
            content: _t("Set the start date of the depreciation (e.g. the acquisition date)."),
            run: "edit 2026-01-01",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='validate']",
            content: markup(_t(
                "Click <b>Confirm Asset</b> to activate the asset. Its state becomes <b>Running</b>."
            )),
            tooltipPosition: "left",
            run: "click",
        },

        // --- Disposal ---
        {
            trigger: "button[name='action_dispose']",
            content: markup(_t(
                "Click <b>Dispose</b> to dispose the asset. The system cancels draft depreciation " +
                "entries and creates a <b>disposal journal entry</b> automatically."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: ".o_control_panel .o_back_button",
            content: markup(_t(
                "The disposal journal entry is opened. Return to the assets list to review the asset."
            )),
            run: "click",
        },
        {
            // Several assets may share the name "Machine A" across runs, and
            // the list is ordered by date_start, not by state. Target the row
            // whose Status column is "Disposed" so we always re-open the asset
            // that actually has the disposal entry (and the Revert button).
            trigger: ".o_list_renderer .o_data_row:has(.o_data_cell[name='state']:contains('Disposed')) .o_data_cell[name='name']:contains('Machine A')",
            content: markup(_t(
                "Re-open the disposed asset <b>Machine A</b> from the list to review its disposal details."
            )),
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: "a.nav-link:contains('Disposal')",
            content: markup(_t(
                "Open the <b>Disposal</b> tab: it shows the <b>disposal date</b>, the generated " +
                "<b>disposal journal entry</b> and the linked documents."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_disposal_reason'] textarea",
            content: markup(_t("Record the <b>Disposal Reason</b> for the audit trail.")),
            run: "edit Sold to third party",
        },
        {
            trigger: ".o_field_widget[name='od19_additional_bill_ids']",
            content: markup(_t(
                "Attach <b>Additional Documents</b> and <b>Supporting Documents</b> (bills / moves) " +
                "related to the disposal."
            )),
            run: "click",
        },
        ...stepUtils.saveForm(),

        // --- Revert disposal ---
        {
            trigger: "button[name='action_revert_disposal']",
            content: markup(_t(
                "If the disposal was a mistake, click <b>Revert Disposal</b>. The disposal entry is " +
                "reversed and the asset goes back to <b>Running</b>."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Asset Disposal complete! The lifecycle is <b>Draft → Running → Disposed</b>, " +
                "with the option to revert. Disposed assets appear in red in the list."
            )),
            run: "click",
        },
    ],
});
