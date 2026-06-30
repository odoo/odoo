import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import { showProductColumn } from "@account/js/tours/tour_utils";

import { markup } from "@odoo/owl";

export const accountTourSteps = {
    draftInvoiceSelector:
        ":has(.o_field_widget[name=move_type] span[raw-value=out_invoice]):has(.o_arrow_button_current[data-value=draft])",
    postedInvoiceSelector:
        ":has(.o_field_widget[name=move_type] span[raw-value=out_invoice]):has(.o_arrow_button_current[data-value=posted])",
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
    endSteps() {
        return [{
            isActive: ["auto"],
            trigger: '.breadcrumb-item',
            run: "click",
        }];
    },
}

registry.category("web_tour.tours").add('account_tour', {
    url: "/odoo",
    steps: () => [
    ...accountTourSteps.goToAccountMenu(markup(_t('Send invoices to your customers in no time with the <b>Invoicing app</b>.'))),
    ...accountTourSteps.onboarding(),
    ...accountTourSteps.newInvoice(),
    {
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=partner_id] .o_input_dropdown`,
        content: markup(_t("Write a customer name to <b>create one</b> or <b>see suggestions</b>.")),
        tooltipPosition: "right",
        run: "click",
    },
    {
        isActive: ["auto"],
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=partner_id] input`,
        run: "edit Test Customer",
    },
    {
        isActive: ["auto"],
        trigger: `body${accountTourSteps.draftInvoiceSelector} .o_m2o_dropdown_option a:contains('Create')`,
        content: _t("Select first partner"),
        run: "click",
    },
    {
        isActive: ["auto"],
        trigger: `body${accountTourSteps.draftInvoiceSelector} .modal-content button.btn-primary`,
        content: markup(_t("Once everything is set, you are good to continue. You will be able to edit this later in the <b>Customers</b> menu.")),
        run: "click",
    },
    {
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] .o_field_x2many_list_row_add a`,
        content: _t("Add a line to your invoice"),
        run: "click",
    },
    ...showProductColumn(),
    {
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] div[name=product_id]`,
        content: _t("Fill in the details of the product or see the suggestion."),
        tooltipPosition: "bottom",
        run: "click",
    },
    {
        isActive: ["auto"],
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] div[name=product_id] input`,
        run: "edit Test Product",
    },
    {
        isActive: ["auto"],
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] div[name=product_id] .o_m2o_dropdown_option_create a:contains(create)`,
        content: _t("Create the product."),
        run: "click",
    },
    {
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] div[name=product_id] button[id=labelVisibilityButtonId]`,
        content: _t("Click here to add a description to your product."),
        tooltipPosition: "bottom",
        run: "click",
    },
    {
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] div[name=product_id] textarea`,
        content: _t("Add a description to your item."),
        tooltipPosition: "bottom",
        run: "edit A very useful description.",
    },
    {
        isActive: ["auto"],
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] div[name=product_id] textarea`,
        run: function () {
            // Since the t-on-change of the input is not triggered by the run: "edit" action,
            // we need to dispatch the event manually requiring a function.
            const input = this.anchor;
            input.dispatchEvent(new InputEvent("input"));
            input.dispatchEvent(new Event("change"));
        },
    },
    {
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] td[name=price_unit]`,
        content: _t("Verify the price and update if necessary."),
        tooltipPosition: "bottom",
        run: "click",
    },
    {
        isActive: ["auto"],
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] div[name=price_unit] input`,
        content: _t("Set a price."),
        run: "edit 100",
    },
    ...stepUtils.saveForm(),
    {
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} button[name=action_post]`,
        content: _t("Once your invoice is ready, confirm it."),
        run: "click",
    },
    {
        trigger: `.o_form_view_container${accountTourSteps.postedInvoiceSelector} button[name=action_invoice_sent]:contains(send)`,
        content: _t("Send the invoice to the customer and check what he'll receive."),
        tooltipPosition: "bottom",
        run: "click",
    },
    {
        // RecipientsInputTagsListPopover will not display if the customer already has an email address
        // unless it's possible to have optional steps, we will only use it for tests at the moment.
        isActive: ["auto"],
        trigger: `body${accountTourSteps.postedInvoiceSelector} .o-mail-RecipientsInputTagsListPopover input`,
        content: markup(_t("Write here <b>your own email address</b> to test the flow.")),
        run: "edit customer@example.com",
    },
    {
        isActive: ["auto"],
        trigger: `body${accountTourSteps.postedInvoiceSelector} .o-mail-RecipientsInputTagsListPopover .btn-primary`,
        content: _t("Validate."),
        run: "click",
    },
    {
        trigger: `body${accountTourSteps.postedInvoiceSelector} .modal button[name=action_send_and_print]`,
        content: _t("Let's send the invoice."),
        tooltipPosition: "top",
        run: "click",
    },
    ...accountTourSteps.endSteps(),
]});
