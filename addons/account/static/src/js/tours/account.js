odoo.define('account.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('account_tour', {
    skip_enabled: true,
    url: "/web",
}, [
    ...tour.stepUtils.goToAppSteps('account.menu_finance', _t('Send invoices to your customers in no time with the <b>Invoicing app</b>.')),
    {
        trigger: "a.o_onboarding_step_action[data-method=action_open_base_onboarding_company]",
        content: _t("Start by checking your company's data."),
    }, {
        trigger: "button[name=action_save_onboarding_company_step]",
        content: _t("Looks good. Let's continue."),
    }, {
        trigger: "a.o_onboarding_step_action[data-method=action_open_base_document_layout]",
        content: _t("Customize your layout."),
    }, {
        trigger: "button[name=document_layout_save]",
        content: _t("Once everything is as you want it, validate."),
    }, {
        trigger: "a.o_onboarding_step_action[data-method=action_open_account_onboarding_create_invoice]",
        content: _t("Now, we'll create a your first invoice."),
    }, {
        trigger: "input[name=name]",
        content: _t("Customize the prefix and number to fit your needs."),
        run: 'text SALE/0000000001'
    }, {
        trigger: "div[name=partner_id] input",
        content: _t("Write a company name to <b>create one</b> or <b>see suggestions</b>."),
        position: "bottom",
    }, {
        trigger: ".o_m2o_dropdown_option a:contains('Create')",
        content: _t("Select first partner"),
        auto: true,
    }, {
        trigger: ".modal-content button.btn-primary",
        content: _t("Once everything is set, you are good to continue. You will be able to edit this later in the <b>Customers</b> menu."),
    }, {
        trigger: "div[name=invoice_line_ids] .o_field_x2many_list_row_add a:not([data-context])",
        content: _t("Add a line to your invoice"),
    }, {
        trigger: "div[name=invoice_line_ids] textarea[name=name]",
        content: _t("Fill in the details of the line.<br><i>Tip: all the details can be set automatically if you configure your <b>products</b>.</i>"),
        position: "bottom",
    }, {
        trigger: "div[name=invoice_line_ids] input[name=price_unit]",
        content: _t("Set a price"),
        position: "bottom",
        run: 'text 100',
    }, {
        trigger: "button[name=action_post]",
        content: _t("Once your invoice is ready, validate."),
    }, {
        trigger: "button[name=action_invoice_sent]",
        content: _t("Send the invoice and check what the customer will receive."),
    }, {
        trigger: "input[name=email]",
        content: _t("Write here <b>your own email address</b> to test the flow."),
        run: 'text customer@example.com',
    }, {
        trigger: ".modal-content button.btn-primary",
        content: _t("Validate."),
    }, {
        trigger: "button[name=send_and_print_action]",
        content: _t("Let's send the invoice."),
    }
]);

});
