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
                run: "click",
            },
        ];
    },
}

registry.category("web_tour.tours").add('account_tour', {
    url: "/odoo",
    steps: () => [
    ...accountTourSteps.goToAccountMenu('Send invoices to your customers in no time with the <b>Invoicing app</b>.'),
    ...accountTourSteps.onboarding(),
    ...accountTourSteps.newInvoice(),
    {
        isActive: ["auto"],
        trigger: "[name=move_type] [raw-value=out_invoice]",
    },
    {
        trigger: "div[name=partner_id] .o_input_dropdown",
        content: markup(_t("Write a customer name to <b>create one</b> or <b>see suggestions</b>.")),
        tooltipPosition: "right",
        run: "click",
    }, {
        isActive: ["auto"],
        trigger: "div[name=partner_id] input",
        run: "edit Test",
    },
    {
        isActive: ["auto"],
        trigger: "[name=move_type] [raw-value=out_invoice]",
    },
    {
        isActive: ["auto"],
        trigger: ".o_m2o_dropdown_option a:contains('Create')",
        content: _t("Select first partner"),
        run: "click",
    },
    {
        isActive: ["auto"],
        trigger: "[name=move_type] [raw-value=out_invoice]",
    },
    {
        isActive: ["auto"],
        trigger: ".modal-content button.btn-primary",
        content: markup(_t("Once everything is set, you are good to continue. You will be able to edit this later in the <b>Customers</b> menu.")),
        run: "click",
    },
    {
        isActive: ["auto"],
        trigger: "[name=move_type] [raw-value=out_invoice]",
    },
    {
        trigger: "div[name=invoice_line_ids] .o_field_x2many_list_row_add a",
        content: _t("Add a line to your invoice"),
        run: "click",
    },
    {
        isActive: ["auto"],
        trigger: "[name=move_type] [raw-value=out_invoice]",
    },
    {
        trigger: "div[name=invoice_line_ids] div[name=product_id] input",
        content: _t("Fill in the details of the line."),
        tooltipPosition: "bottom",
        run: "edit Test",
    },
    {
        isActive: ["auto"],
        trigger: "[name=move_type] [raw-value=out_invoice]",
    },
    {
        trigger: "div[name=invoice_line_ids] div[name=price_unit] input",
        content: _t("Set a price"),
        tooltipPosition: "bottom",
        run: "edit 100",
    },
    ...stepUtils.saveForm(),
    {
        isActive: ["auto"],
        trigger: "button.o_form_button_create",
    },
    {
        trigger: "button[name=action_post]",
        content: _t("Once your invoice is ready, confirm it."),
        run: "click",
    },
    {
        isActive: ["auto"],
        trigger: "[name=move_type] [raw-value=out_invoice]",
    },
    {
        trigger: "button[name=action_invoice_sent]:contains(print & send)",
        content: _t("Send the invoice to the customer and check what he'll receive."),
        tooltipPosition: "bottom",
        run: "click",
    },
    {
        isActive: ["auto"],
        trigger: "div.modal-dialog",
    },
    {
        trigger: ".modal button[name=document_layout_save]",
        content: _t("Configure document layout."),
        run: "click",
    },
    {
        content: "Check sending method: 'email'",
        trigger: "input[id='email']",
        run: "click",
    },
    {
        trigger: "div[name=account_missing_email] a",
        content: _t("Complete the partner data with email"),
        run: "click",
    }, {
        isActive: ["auto"],
        trigger: ".o_field_widget[name=email] input, input[name=email]",
        content: markup(_t("Write here <b>your own email address</b> to test the flow.")),
        run: "edit customer@example.com",
    },
    ...stepUtils.saveForm(),
    {
        trigger: '.breadcrumb .o_back_button',
        content: _t('Go back'),
        tooltipPosition: 'bottom',
        run: "click",
    },
    {
        isActive: ["auto"],
        trigger: "[name=move_type] [raw-value=out_invoice], [name=move_type][raw-value=out_invoice]",
    },
    {
        trigger: "button[name=action_invoice_sent]:contains(print & send)",
        content: _t("Send the invoice and check what the customer will receive."),
        run: "click",
    },
    {
        isActive: ["auto"],
        trigger: "[name=move_type] [raw-value=out_invoice]",
    },
    {
        trigger: ".modal button[name=action_send_and_print]",
        content: _t("Let's send the invoice."),
        tooltipPosition: "top",
        run: "click",
    },
    {
        isActive: ["auto"],
        trigger: "body:has(.o_form_saved)",
    },
    {
        trigger: "button[name=action_register_payment]:contains(pay):enabled",
        content: _t("The button priority shifted since the invoice has been sent. Let's register the payment now."),
        tooltipPosition: "bottom",
    },
]});
