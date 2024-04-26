/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import { markup } from "@odoo/owl";

export const accountTourSteps = {
    goToAccountMenu(description="Open Invoicing Menu") {
        return stepUtils.goToAppSteps('account.menu_finance', description);
    },
    onboarding() {
        return [];
    },
    newInvoice() {
        return [
            {
                trigger: "button.o_list_button_add",
                content: _t("Now, we'll create your first invoice"),
            },
        ];
    },
}

registry.category("web_tour.tours").add('account_tour', {
    url: "/web",
    sequence: 60,
    steps: () => [
    ...accountTourSteps.goToAccountMenu('Send invoices to your customers in no time with the <b>Invoicing app</b>.'),
    ...accountTourSteps.onboarding(),
    ...accountTourSteps.newInvoice(),
    {
        trigger: "div[name=partner_id] .o_input_dropdown",
        extra_trigger: "[name=move_type] [raw-value=out_invoice]",
        content: markup(_t("Write a customer name to <b>create one</b> or <b>see suggestions</b>.")),
        position: "right",
        run: "click",
    }, {
        trigger: "div[name=partner_id] input",
        run: "edit Test",
        auto: true,
    }, {
        trigger: ".o_m2o_dropdown_option a:contains('Create')",
        extra_trigger: "[name=move_type] [raw-value=out_invoice]",
        content: _t("Select first partner"),
        auto: true,
        run: "click",
    }, {
        trigger: ".modal-content button.btn-primary",
        extra_trigger: "[name=move_type] [raw-value=out_invoice]",
        content: markup(_t("Once everything is set, you are good to continue. You will be able to edit this later in the <b>Customers</b> menu.")),
        auto: true,
        run: "click",
    }, {
        trigger: "div[name=invoice_line_ids] .o_field_x2many_list_row_add a",
        extra_trigger: "[name=move_type] [raw-value=out_invoice]",
        content: _t("Add a line to your invoice"),
        run: "click",
    }, {
        trigger: "div[name=invoice_line_ids] div[name=product_id] input",
        extra_trigger: "[name=move_type] [raw-value=out_invoice]",
        content: _t("Fill in the details of the line."),
        position: "bottom",
        run: "edit Test",
    }, {
        trigger: "div[name=invoice_line_ids] div[name=price_unit] input",
        extra_trigger: "[name=move_type] [raw-value=out_invoice]",
        content: _t("Set a price"),
        position: "bottom",
        run: "edit 100",
    },
    ...stepUtils.saveForm(),
    {
        trigger: "button[name=action_post]",
        extra_trigger: "button.o_form_button_create",
        content: _t("Once your invoice is ready, confirm it."),
        run: "click",
    }, {
        trigger: "button[name=action_invoice_sent]",
        extra_trigger: "[name=move_type] [raw-value=out_invoice]",
        content: _t("Send the invoice to the customer and check what he'll receive."),
        position: "bottom",
        run: "click",
    }, {
        trigger: "button[name=document_layout_save]",
        extra_trigger: "div.modal-dialog",
        content: _t("Configure document layout."),
    },
    {
        trigger: "div[name=partner_missing_email] a",
        extra_trigger: "[name=move_type] [raw-value=out_invoice]",
        content: _t("Complete the partner data with email"),
        run: "click",
    }, {
        trigger: ".o_field_widget[name=email] input, input[name=email]",
        content: markup(_t("Write here <b>your own email address</b> to test the flow.")),
        run: "edit customer@example.com",
        auto: true,
    },
    ...stepUtils.saveForm(),
    {
        trigger: '.breadcrumb .o_back_button',
        content: _t('Go back'),
        position: 'bottom',
        run: "click",
    }, {
        trigger: "button[name=action_invoice_sent]",
        extra_trigger: "[name=move_type] [raw-value=out_invoice], [name=move_type][raw-value=out_invoice]",
        content: _t("Send the invoice and check what the customer will receive."),
        run: "click",
    }, {
        trigger: "button[name=action_send_and_print]",
        extra_trigger: "[name=move_type] [raw-value=out_invoice]",
        content: _t("Let's send the invoice."),
        position: "top",
        run: "click",
    }, {
        trigger: "button[name=action_register_payment]",
        content: _t("The button priority shifted since the invoice has been sent. Let's register the payment now."),
        position: "bottom",
        run() {},
    }
]});
