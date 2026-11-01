import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Accounting Tour
 *
 * Walks the user through:
 *  1. Petty Cash Fund setup and transactions
 *  2. WHT (Withholding Tax) on payments
 *  3. Fixed Assets and depreciation
 *  4. Fiscal Year management and year-end closing
 */
registry.category("web_tour.tours").add("od19_accounting_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's explore the <b>Accounting</b> module: Petty Cash, WHT, Fixed Assets, and Fiscal Year."))
        ),

        // --- Petty Cash Fund ---
        {
            trigger: navSection("Petty Cash"),
            content: markup(_t("Open the <b>Petty Cash</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Funds"),
            content: markup(_t("Open <b>Funds</b> to manage small cash funds.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Petty Cash Funds"),
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new petty cash fund."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the fund name (e.g. Office Petty Cash)."),
            run: "edit Office Petty Cash",
        },
        {
            trigger: ".o_field_widget[name='account_id'] input",
            content: _t("Select the cash GL account."),
            run: "click",
        },
        {
            trigger: ".o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='amount'] input",
            content: markup(_t("Set the <b>fund amount</b>. The balance is updated automatically by transactions.")),
            run: "edit 5000",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "a.nav-link:contains('Transactions')",
            content: markup(_t(
                "Open the <b>Transactions</b> page to record petty cash inflows and outflows. " +
                "Each transaction updates the fund balance."
            )),
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- WHT on Payment ---
        {
            trigger: navSection("Vendors"),
            content: markup(_t("Open the <b>Vendors</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Payments"),
            content: markup(_t(
                "Open <b>Payments</b> to record vendor/customer payments with <b>Withholding Tax (WHT)</b>."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new payment."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: _t("Select the vendor or customer."),
            run: "click",
        },
        {
            trigger: ".o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='amount'] input",
            content: _t("Enter the payment amount."),
            run: "edit 10000",
        },
        {
            trigger: ".o_field_widget[name='od19_wht_type_id'] input",
            content: markup(_t(
                "The <b>WHT Type</b> (Withholding Tax, optional) drives the automatic WHT base, " +
                "WHT amount and net amount on the payment."
            )),
            run: "click",
        },
        // Do NOT pick an entry from the suggestion list: in a database where no
        // Withholding Tax Type exists yet the only entry is a "Create ..."
        // option. Its dialog requires a dedicated WHT account (none is
        // pre-seeded), so it cannot be saved and would block the rest of the
        // tour. Showing the list is enough; the tour continues with the save.
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        // --- Asset Profile (required before an asset can be saved) ---
        // Creating an asset needs a profile, and a fresh database has none.
        // Create one first, otherwise the asset save fails on the required
        // `profile_id` and the tour gets stuck.
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
            content: markup(_t("Select the <b>Residual Value Account</b>.")),
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

        // --- Fixed Assets ---
        {
            trigger: navSection("Assets"),
            content: markup(_t("Open the <b>Assets</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Assets"),
            content: markup(_t("Open <b>Fixed Assets</b> to manage assets and depreciation.")),
            tooltipPosition: "bottom",
            run: "click",
        },
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
            content: _t("Enter the asset name (e.g. Company Vehicle)."),
            run: "edit Company Vehicle",
        },
        {
            trigger: ".o_field_widget[name='purchase_value'] input",
            content: _t("Enter the purchase value."),
            run: "edit 500000",
        },
        {
            trigger: ".o_field_widget[name='salvage_value'] input",
            content: _t("Enter the salvage (residual) value."),
            run: "edit 50000",
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
                "Click <b>Validate</b> to activate the asset. The depreciation schedule is generated automatically."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "a.nav-link:contains('Depreciation Board')",
            content: markup(_t(
                "Open the <b>Depreciation Board</b> page. Each line shows a depreciation entry; " +
                "click <b>Create Move</b> to post it."
            )),
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Fiscal Year ---
        {
            trigger: navSection("Configuration"),
            content: markup(_t("Open the <b>Configuration</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Fiscal Years"),
            content: markup(_t("Open <b>Fiscal Years</b> to define accounting periods.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new fiscal year."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the fiscal year name (e.g. FY 2026)."),
            run: "edit FY 2026",
        },
        {
            trigger: ".o_field_widget[name='date_from'] .o_input",
            content: _t("Set the start date of the fiscal year."),
            run: "edit 2026-01-01",
        },
        {
            trigger: ".o_field_widget[name='date_to'] .o_input",
            content: _t("Set the end date of the fiscal year."),
            run: "edit 2026-12-31",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: markup(_t(
                "Fiscal years cannot overlap, so this demo form is <b>kept unsaved</b> and " +
                "discarded to avoid clashing with the periods already defined in your database."
            )),
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu for the year-end statements.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-item:contains('NPAE Financial Statement')",
            content: markup(_t(
                "At the end of the year, file the <b>NPAE financial statement</b> " +
                "(งบการเงินตามแบบ NPAE) with the Revenue Department."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },

        {
            trigger: ".o_dialog .modal-title",
            content: markup(_t(
                "Accounting tour complete! You've learned <b>petty cash</b> fund management, " +
                "<b>WHT</b> on payments, <b>fixed asset</b> depreciation, and <b>fiscal year</b> " +
                "management with year-end reporting."
            )),
            run: "click",
        },
    ],
});
