odoo.define('l10n_eg_edi_eta.account_tour', function (require) {
"use strict";

require('account.tour');

var core = require('web.core');
let session = require('web.session');
let tour = require('web_tour.tour');

var _t = core._t;

if (session.company_account_fiscal_country_code === 'EG') {

    const accountTour = tour.tours.account_tour;
    const companyName = session.company_name;

    let stepsToAdd = [
    // Configure ETA settings on the Customer Invoices journal
    {
        trigger: 'button[data-menu-xmlid="account.menu_finance_configuration"]',
        extra_trigger: 'body:not(:has(span:contains("Unsaved changes")))',
        content: _t("Let's configure ETA settings on the Customer Invoices journal."),
        position: "bottom",
        run: "click",
    }, {
        trigger: 'a[data-menu-xmlid="account.menu_action_account_journal_form"]',
        content: _t("Open the Journals."),
        position: "right",
        run: "click",
    }, {
        trigger: 'td[name=code]:contains("INV")',
        content: _t("Select the Customer Invoice journal."),
        position: "bottom",
        run: "click",
    }, {
        trigger: '.o_form_button_edit',
        content: _t("Edit the journal."),
        position: "bottom",
        run: "click",
    }, {
        trigger: 'a:contains("' + _t('Advanced Settings') + '")',
        extra_trigger: '.o_form_button_save',
        content: _t("Select Advanced Settings tab."),
        position: "bottom",
        run: "click",
    }, {
        trigger: "div[name=l10n_eg_branch_id] input",
        content: _t("Set the Branch"),
        position: "bottom",
        run: "text " + companyName,
    }, {
        trigger: ".ui-menu-item > a:contains('" + companyName + "').ui-state-active",
        auto: true,
        in_modal: false,
    }, {
        trigger: "div[name=l10n_eg_activity_type_id] input",
        content: _t("Set the ETA Activity Code"),
        position: "bottom",
    }, {
        trigger: ".ui-menu-item > a",
        auto: true,
        in_modal: false,
    }, {
        trigger: "input[name=l10n_eg_branch_identifier]",
        content: _t("Set the ETA Branch ID	"),
        position: "bottom",
        run: "text ABCD123456789",
    }, {
        trigger: '.o_form_button_save',
        content: _t("Save the journal."),
        position: "bottom",
        run: "click",
    },
    // Set the building number on the branch (required field for the invoice)
    {
        trigger: "a[name=l10n_eg_branch_id]",
        content: _t("Let's set the building number on the branch."),
        position: "bottom",
        run: "click",
    }, {
        trigger: '.o_form_button_edit',
        extra_trigger: 'span[name=l10n_eg_building_no]',
        content: _t("Edit the branch."),
        position: "bottom",
    }, {
        trigger: 'input[name=l10n_eg_building_no]',
        content: _t("Set a building number."),
        position: "bottom",
        run: "text 112",
    }, {
        trigger: '.o_form_button_save',
        content: _t("Save the branch."),
        position: "bottom",
        run: "click",
    }, {
        trigger: 'a[data-menu-xmlid="account.menu_finance"], a[data-menu-xmlid="account_accountant.menu_accounting"]',
        content: _t("Go back to dashboard."),
        position: "bottom",
        run: "click",
    }];


    let addIndex = accountTour.steps.findIndex(({trigger}) => trigger === 'button[name=action_save_onboarding_company_step]');
    accountTour.steps.splice(addIndex + 1, 0, ...stepsToAdd);

    stepsToAdd = [
    // Fill all required fields in the customer details
    {
        trigger: "input[name=l10n_eg_building_no]",
        position: "right",
        content: _t("Set a building number."),
        run: "text 123",
    }, {
        trigger: "input[name=street]",
        position: "right",
        content: "Set a Street",
        run: "text Test Street 123",
    }, {
        trigger: "input[name=city]",
        position: "right",
        content: "Set a City",
        run: "text Alexandria",
    }, {
        trigger: "input[name=zip]",
        position: "right",
        content: "Set a Zip Code",
        run: "text 39020",
    }, {
        trigger: "div[name=state_id] input",
        position: "right",
        content: "Set a State",
        run: "text Alexandria",
    }, {
        trigger: ".ui-menu-item > a:contains('Alexandria (EG)').ui-state-active",
        auto: true,
        in_modal: false,
    }, {
        trigger: "div[name=country_id] input",
        position: "right",
        content: "Set a Country",
        run: "text Egypt",
    }, {
        trigger: ".ui-menu-item > a:contains('Egypt').ui-state-active",
        auto: true,
        in_modal: false,
    }, {
        trigger: "div[name=vat] input",
        position: "bottom",
        content: "Set a VAT",
        run: "text 12345678-9",
    }];

    addIndex = accountTour.steps.findIndex(({trigger}) => trigger === 'div[name=partner_id] input');
    accountTour.steps.splice(addIndex + 2, 0, ...stepsToAdd);

    stepsToAdd = [
    // Make sure the EGS/GS1 Barcode is set correctly on product (auto only)
    {
        trigger: ".o_field_widget[name=product_id] input, .o_field_widget[name=product_template_id] input",
        content: _t("Select a product, or create a new one on the fly."),
        auto: true,
        position: "right",
    }, {
        trigger: ".ui-menu-item > a",
        auto: true,
        in_modal: false,
    }, {
        trigger: ".o_field_widget[name=product_id] button, .o_field_widget[name=product_template_id] button",
        content: _t("Select a product, or create a new one on the fly."),
        auto: true,
        position: "right",
    }, {
        trigger: 'a:contains("' + _t('Accounting') + '")',
        extra_trigger: '.modal-content button.btn-primary',
        content: _t("Select Accounting tab."),
        position: "bottom",
        auto: true,
        run: "click",
    }, {
        trigger: "input[name=l10n_eg_eta_code]",
        position: "bottom",
        content: "Set an ETA Code",
        auto: true,
        run: "text ABCD123456798",
    }, {
        trigger: ".modal-content button.btn-primary",
        content: _t("Save the product."),
        auto: true,
    }, {
        trigger: "div[name=invoice_line_ids] span[name=name]",
        content: _t("Fill in the details of the line."),
        auto: true,
        position: "bottom",
    }];

    addIndex = accountTour.steps.findIndex(({trigger}) => trigger === 'div[name=invoice_line_ids] .o_field_x2many_list_row_add a:not([data-context])');
    accountTour.steps.splice(addIndex + 1, 0, ...stepsToAdd);
}
});
