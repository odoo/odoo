import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import { accountTourSteps } from "@account/js/tours/account";
import { showProductColumn } from "@account/js/tours/tour_utils";

registry.category("web_tour.tours").add("account_tour_test", {
    steps: () => [
        ...accountTourSteps.goToAccountMenu("Send invoices to your customers in no time with the Invoicing app."),
        ...accountTourSteps.onboarding(),
        ...accountTourSteps.newInvoice(),
        {
            trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=partner_id] .o_input_dropdown`,
            content: "Write a customer name to create one or see suggestions.",
            run: "click",
        },
        {
            trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=partner_id] input`,
            run: "edit Test Customer",
        },
        {
            trigger: `body${accountTourSteps.draftInvoiceSelector} .o_m2o_dropdown_option a:contains('Create')`,
            content: "Select first partner",
            run: "click",
        },
        {
            trigger: `body${accountTourSteps.draftInvoiceSelector} .modal-content button.btn-primary`,
            content: "Once everything is set, you are good to continue. You will be able to edit this later in the Customers menu.",
            run: "click",
        },
        {
            trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] .o_field_x2many_list_row_add button`,
            content: "Add a line to your invoice",
            run: "click",
        },
        ...showProductColumn(),
        {
            trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] div[name=product_id]`,
            content: "Fill in the details of the product or see the suggestion.",
            run: "click",
        },
        {
            trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] div[name=product_id] input`,
            run: "edit Test Product",
        },
        {
            trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] div[name=product_id] .o_m2o_dropdown_option_create a:contains(create)`,
            content: "Create the product.",
            run: "click",
        },
        {
            trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] div[name=name] textarea`,
            content: "Add a description to your item.",
            run: "edit A very useful description.",
        },
        {
            trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] div[name=name] textarea`,
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
            content: "Verify the price and update if necessary.",
            run: "click",
        },
        {
            trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] div[name=price_unit] input`,
            content: "Set a price.",
            run: "edit 100",
        },
        ...stepUtils.saveForm(),
        {
            trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} button[name=action_post]`,
            content: "Once your invoice is ready, confirm it.",
            run: "click",
        },
        {
            trigger: `.o_form_view_container${accountTourSteps.postedInvoiceSelector} button[name=action_invoice_sent]:contains(send)`,
            content: "Send the invoice to the customer and check what he'll receive.",
            run: "click",
        },
        {
            content: "Wait for animation frame",
            trigger: `body${accountTourSteps.postedInvoiceSelector} .o-mail-RecipientsInputTagsListPopover input`,
        },
        {
            trigger: `body${accountTourSteps.postedInvoiceSelector} .o-mail-RecipientsInputTagsListPopover input`,
            content: "Write here your own email address to test the flow.",
            run: "edit customer@example.com",
        },
        {
            trigger: `body${accountTourSteps.postedInvoiceSelector} .o-mail-RecipientsInputTagsListPopover .btn-primary`,
            content: "Validate.",
            run: "click",
        },
        {
            trigger: `body${accountTourSteps.postedInvoiceSelector} .modal button[name=action_send_and_print]`,
            content: "Let's send the invoice.",
            run: "click",
        },
        ...accountTourSteps.endSteps(),
    ],
});
