odoo.define('account.tour', function(require) {
"use strict";

var core = require('web.core');
const {Markup} = require('web.utils');
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
        position: "bottom",
    }, {
        trigger: "a.o_onboarding_step_action[data-method=action_open_base_document_layout]",
        content: _t("Customize your layout."),
        position: "bottom",
    }, {
        trigger: "button[name=document_layout_save]",
        extra_trigger: "a.o_onboarding_step_action[data-method=action_open_base_document_layout]",
        content: _t("Once everything is as you want it, validate."),
        position: "top",
    }, {
        trigger: "a.o_onboarding_step_action[data-method=action_open_account_onboarding_create_invoice]",
        content: _t("Now, we'll create your first invoice."),
        position: "bottom",
    }, {
        trigger: "div[name=partner_id] input",
        // FIXME WOWL: this selector needs to work in both legacy and non-legacy views
        // because account_invoice_extracts *adds* a js_class on the base view which forces
        // the use of a legacy view in enterprise only
        extra_trigger: "[name=move_type] [raw-value=out_invoice], [name=move_type][raw-value=out_invoice]",
        content: Markup(_t("Write a company name to <b>create one</b> or <b>see suggestions</b>.")),
        position: "right",
    }, {
        trigger: ".o_m2o_dropdown_option a:contains('Create')",
        // FIXME WOWL: this selector needs to work in both legacy and non-legacy views
        // because account_invoice_extracts *adds* a js_class on the base view which forces
        // the use of a legacy view in enterprise only
        extra_trigger: "[name=move_type] [raw-value=out_invoice], [name=move_type][raw-value=out_invoice]",
        content: _t("Select first partner"),
        auto: true,
    }, {
        trigger: ".modal-content button.btn-primary",
        // FIXME WOWL: this selector needs to work in both legacy and non-legacy views
        // because account_invoice_extracts *adds* a js_class on the base view which forces
        // the use of a legacy view in enterprise only
        extra_trigger: "[name=move_type] [raw-value=out_invoice], [name=move_type][raw-value=out_invoice]",
        content: Markup(_t("Once everything is set, you are good to continue. You will be able to edit this later in the <b>Customers</b> menu.")),
        auto: true,
    }, {
        trigger: "div[name=invoice_line_ids] .o_field_x2many_list_row_add a",
        // FIXME WOWL: this selector needs to work in both legacy and non-legacy views
        // because account_invoice_extracts *adds* a js_class on the base view which forces
        // the use of a legacy view in enterprise only
        extra_trigger: "[name=move_type] [raw-value=out_invoice], [name=move_type][raw-value=out_invoice]",
        content: _t("Add a line to your invoice"),
    }, {
        trigger: "div[name=invoice_line_ids] div[name=name] textarea",
        // FIXME WOWL: this selector needs to work in both legacy and non-legacy views
        // because account_invoice_extracts *adds* a js_class on the base view which forces
        // the use of a legacy view in enterprise only
        extra_trigger: "[name=move_type] [raw-value=out_invoice], [name=move_type][raw-value=out_invoice]",
        content: _t("Fill in the details of the line."),
        position: "bottom",
    }, {
        trigger: "div[name=invoice_line_ids] div[name=price_unit] input",
        // FIXME WOWL: this selector needs to work in both legacy and non-legacy views
        // because account_invoice_extracts *adds* a js_class on the base view which forces
        // the use of a legacy view in enterprise only
        extra_trigger: "[name=move_type] [raw-value=out_invoice], [name=move_type][raw-value=out_invoice]",
        content: _t("Set a price"),
        position: "bottom",
        run: 'text 100',
    },
    ...tour.stepUtils.saveForm(),
    {
        trigger: "button[name=action_post]",
        extra_trigger: "button.o_form_button_edit",
        content: _t("Once your invoice is ready, press CONFIRM."),
    }, {
        trigger: "button[name=action_invoice_sent]",
        // FIXME WOWL: this selector needs to work in both legacy and non-legacy views
        // because account_invoice_extracts *adds* a js_class on the base view which forces
        // the use of a legacy view in enterprise only
        extra_trigger: "[name=move_type] [raw-value=out_invoice], [name=move_type][raw-value=out_invoice]",
        content: _t("Send the invoice and check what the customer will receive."),
    }, {
        trigger: "input[name=email]",
        // FIXME WOWL: this selector needs to work in both legacy and non-legacy views
        // because account_invoice_extracts *adds* a js_class on the base view which forces
        // the use of a legacy view in enterprise only
        extra_trigger: "[name=move_type] [raw-value=out_invoice], [name=move_type][raw-value=out_invoice]",
        content: Markup(_t("Write here <b>your own email address</b> to test the flow.")),
        run: 'text customer@example.com',
        auto: true,
    }, {
        trigger: ".modal-content button.btn-primary",
        // FIXME WOWL: this selector needs to work in both legacy and non-legacy views
        // because account_invoice_extracts *adds* a js_class on the base view which forces
        // the use of a legacy view in enterprise only
        extra_trigger: "[name=move_type] [raw-value=out_invoice], [name=move_type][raw-value=out_invoice]",
        content: _t("Validate."),
        auto: true,
    }, {
        trigger: "button[name=send_and_print_action]",
        // FIXME WOWL: this selector needs to work in both legacy and non-legacy views
        // because account_invoice_extracts *adds* a js_class on the base view which forces
        // the use of a legacy view in enterprise only
        extra_trigger: "[name=move_type] [raw-value=out_invoice], [name=move_type][raw-value=out_invoice]",
        content: _t("Let's send the invoice."),
        position: "top"
    }, {
        trigger: "button[name=action_invoice_sent].btn-secondary",
        content: _t("The invoice having been sent, the button has changed priority."),
        run() {},
    }, {
        trigger: "button[name=action_register_payment]",
        content: _t("The next step is payment registration."),
        run() {},
    }
]);

});
