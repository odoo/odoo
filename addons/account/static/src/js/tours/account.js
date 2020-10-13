odoo.define('account.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('account_tour', {
    url: "/web",
    sequence: 60,
}, [
    ...tour.stepUtils.goToAppSteps('account.menu_finance', _t('Send invoices to your customers in no time with the <b>Invoicing app</b>.')),
    {
        trigger: "a.o_onboarding_step_action[data-method=action_open_base_onboarding_company]",
        content: _t("Start by checking your company's data."),
        position: "bottom",
    }, {
        trigger: "button[name=action_save_onboarding_company_step]",
        extra_trigger: "a.o_onboarding_step_action[data-method=action_open_base_onboarding_company]",
        content: _t("Looks good. Let's continue."),
    }, {
        trigger: "a.o_onboarding_step_action[data-method=action_open_base_document_layout]",
        content: _t("Customize your layout."),
        position: "bottom",
    }, {
        trigger: "button[name=document_layout_save]",
        extra_trigger: "a.o_onboarding_step_action[data-method=action_open_base_document_layout]",
        content: _t("Once everything is as you want it, validate."),
    }, {
        trigger: "a.o_onboarding_step_action[data-method=action_open_account_onboarding_create_invoice]",
        content: _t("Now, we'll create your first invoice."),
        position: "bottom",
    }, {
        trigger: "div[name=partner_id] input",
        extra_trigger: "[name=move_type][raw-value=out_invoice]",
        content: _t("Write a company name to <b>create one</b> or <b>see suggestions</b>."),
        position: "bottom",
    }, {
        trigger: ".o_m2o_dropdown_option a:contains('Create')",
        extra_trigger: "[name=move_type][raw-value=out_invoice]",
        content: _t("Select first partner"),
        auto: true,
    }, {
        trigger: ".modal-content button.btn-primary",
        extra_trigger: "[name=move_type][raw-value=out_invoice]",
        content: _t("Once everything is set, you are good to continue. You will be able to edit this later in the <b>Customers</b> menu."),
        auto: true,
    }, {
        trigger: "div[name=invoice_line_ids] .o_field_x2many_list_row_add a:not([data-context])",
        extra_trigger: "[name=move_type][raw-value=out_invoice]",
        content: _t("Add a line to your invoice"),
    }, {
        trigger: "div[name=invoice_line_ids] textarea[name=name]",
        extra_trigger: "[name=move_type][raw-value=out_invoice]",
        content: _t("Fill in the details of the line."),
        position: "bottom",
    }, {
        trigger: "div[name=invoice_line_ids] input[name=price_unit]",
        extra_trigger: "[name=move_type][raw-value=out_invoice]",
        content: _t("Set a price"),
        position: "bottom",
        run: 'text 100',
    }, {
        trigger: "button[name=action_post]",
        extra_trigger: "[name=move_type][raw-value=out_invoice]",
        content: _t("Once your invoice is ready, press CONFIRM."),
    }, {
        trigger: "button[name=action_invoice_sent]",
        extra_trigger: "[name=move_type][raw-value=out_invoice]",
        content: _t("Send the invoice and check what the customer will receive."),
    }, {
        trigger: "input[name=email]",
        extra_trigger: "[name=move_type][raw-value=out_invoice]",
        content: _t("Write here <b>your own email address</b> to test the flow."),
        run: 'text customer@example.com',
        auto: true,
    }, {
        trigger: ".modal-content button.btn-primary",
        extra_trigger: "[name=move_type][raw-value=out_invoice]",
        content: _t("Validate."),
        auto: true,
    }, {
        trigger: "button[name=send_and_print_action]",
        extra_trigger: "[name=move_type][raw-value=out_invoice]",
        content: _t("Let's send the invoice."),
    }
]);

});
