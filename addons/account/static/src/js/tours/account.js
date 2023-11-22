/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('account_tour', {
    url: "/web",
    sequence: 60,
    steps: () => [
    ...stepUtils.goToAppSteps('account.menu_finance', markup(_t('Send invoices to your customers in no time with the <b>Invoicing app</b>.'))),
    {
        trigger: "a.o_onboarding_step_action[data-method=action_open_step_company_data]",
        content: _t("Start by checking your company's data."),
        position: "bottom",
        skip_trigger: 'a[data-method=action_open_step_company_data].o_onboarding_step_action__done',
    }, {
        trigger: "button.o_form_button_save",
        extra_trigger: "a.o_onboarding_step_action[data-method=action_open_step_company_data]",
        content: _t("Fill your company data and let's continue."),
        position: "bottom",
        skip_trigger: 'a[data-method=action_open_step_company_data].o_onboarding_step_action__done',
    }, {
        trigger: "a.o_onboarding_step_action[data-method=action_open_step_base_document_layout]",
        content: _t("Customize your layout."),
        position: "bottom",
        skip_trigger: 'a[data-method=action_open_step_base_document_layout].o_onboarding_step_action__done',
    }, {
        trigger: "button[name=document_layout_save]",
        extra_trigger: "a.o_onboarding_step_action[data-method=action_open_step_base_document_layout]",
        content: _t("Once everything is as you want it, validate."),
        position: "top",
        skip_trigger: 'a[data-method=action_open_step_base_document_layout].o_onboarding_step_action__done',
    }, {
        trigger: "a.o_onboarding_step_action[data-method=action_open_step_create_invoice]",
        content: _t("Now, we'll create your first invoice."),
        position: "bottom",
    }, {
        trigger: "div[name=partner_id] .o_input_dropdown",
        extra_trigger: "[name=move_type] [raw-value=out_invoice]",
        content: markup(_t("Write a customer name to <b>create one</b> or <b>see suggestions</b>.")),
        position: "right",
    }, {
        trigger: "div[name=partner_id] input",
        auto: true,
    }, {
        trigger: ".o_m2o_dropdown_option a:contains('Create')",
        extra_trigger: "[name=move_type] [raw-value=out_invoice]",
        content: _t("Select first partner"),
        auto: true,
    }, {
        trigger: ".modal-content button.btn-primary",
        extra_trigger: "[name=move_type] [raw-value=out_invoice]",
        content: markup(_t("Once everything is set, you are good to continue. You will be able to edit this later in the <b>Customers</b> menu.")),
        auto: true,
    }, {
        trigger: "div[name=invoice_line_ids] .o_field_x2many_list_row_add a",
        extra_trigger: "[name=move_type] [raw-value=out_invoice]",
        content: _t("Add a line to your invoice"),
    }, {
        trigger: "div[name=invoice_line_ids] div[name=name] textarea",
        extra_trigger: "[name=move_type] [raw-value=out_invoice]",
        content: _t("Fill in the details of the line."),
        position: "bottom",
    }, {
        trigger: "div[name=invoice_line_ids] div[name=price_unit] input",
        extra_trigger: "[name=move_type] [raw-value=out_invoice]",
        content: _t("Set a price"),
        position: "bottom",
        run: 'text 100',
    },
    ...stepUtils.saveForm(),
    {
        trigger: "button[name=action_post]",
        extra_trigger: "button.o_form_button_create",
        content: _t("After the data extraction, check and validate the bill. If no vendor has been found, add one before validating."),
    }, {
        trigger: "button[name=action_invoice_sent]",
        extra_trigger: "[name=move_type] [raw-value=out_invoice]",
        content: _t("Send the invoice to the customer and check what he'll receive."),
        position: "bottom",
    }, {
        trigger: "button[name=action_open_partners_without_email]",
        extra_trigger: "[name=move_type] [raw-value=out_invoice], [name=move_type][raw-value=out_invoice]",
        content: _t("Complete the partner data with email"),
    }, {
        trigger: ".o_field_widget[name=email] input, input[name=email]",
        content: markup(_t("Write here <b>your own email address</b> to test the flow.")),
        run: 'text customer@example.com',
        auto: true,
    },
    ...stepUtils.saveForm(),
    {
        trigger: '.breadcrumb .o_back_button',
        content: _t('Go back'),
        position: 'bottom',
    }, {
        trigger: "button[name=action_invoice_sent]",
        extra_trigger: "[name=move_type] [raw-value=out_invoice], [name=move_type][raw-value=out_invoice]",
        content: _t("Send the invoice and check what the customer will receive."),
    }, {
        trigger: "button[name=action_send_and_print]",
        extra_trigger: "[name=move_type] [raw-value=out_invoice]",
        content: _t("Let's send the invoice."),
        position: "top",
    }, {
        trigger: "button[name=action_register_payment]",
        content: _t("The button priority shifted since the invoice has been sent. Let's register the payment now."),
        position: "bottom",
        run() {},
    }
]});
